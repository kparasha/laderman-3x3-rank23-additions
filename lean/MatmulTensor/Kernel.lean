/-!
# Exact 3×3 matrix-multiplication tensor kernel
-/

namespace MatmulTensor

/-- A rank-`r` scheme: three `r × 9` integer factor matrices. -/
structure Scheme where
  u : Array (Array Int)
  v : Array (Array Int)
  w : Array (Array Int)
  deriving Repr

def Scheme.rank (s : Scheme) : Nat := s.u.size

def Scheme.support (s : Scheme) : Nat :=
  Id.run do
    let mut n := 0
    for M in #[s.u, s.v, s.w] do
      for row in M do
        for x in row do
          if x ≠ 0 then n := n + 1
    pure n

/-- Target of the matrix-multiplication tensor under hill conventions:
A,B row-major; C reconstructed with W column-major (`3*col+row`). -/
def target (a b c : Nat) : Int :=
  let row := a / 3
  let inner := a % 3
  let bInner := b / 3
  let col := b % 3
  if inner == bInner && c == 3 * col + row then 1 else 0

def coeff (M : Array (Array Int)) (t i : Nat) : Int :=
  (M[t]!)[i]!

/-- Sum_t U[t,a] * V[t,b] * W[t,c] -/
def brentValue (s : Scheme) (a b c : Nat) : Int :=
  Id.run do
    let mut acc : Int := 0
    for t in [0:s.rank] do
      acc := acc + coeff s.u t a * coeff s.v t b * coeff s.w t c
    pure acc

def brentOK (s : Scheme) : Bool :=
  Id.run do
    let mut ok := true
    for a in [0:9] do
      for b in [0:9] do
        for c in [0:9] do
          if brentValue s a b c ≠ target a b c then
            ok := false
    pure ok

/-- Naive additive cost from sparse linear forms (no CSE). -/
def naiveAdditions (s : Scheme) : Nat :=
  Id.run do
    let mut n := 0
    for M in #[s.u, s.v, s.w] do
      for row in M do
        let nnz := (row.filter (· ≠ 0)).size
        if nnz > 0 then n := n + (nnz - 1)
    pure n

end MatmulTensor
