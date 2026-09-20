import MatmulTensor.Kernel

/-!
# Smirnov 2013

Smirnov's rank-23 construction reports a naive additive cost of 84
(Computational Mathematics and Mathematical Physics, 2013).
A machine-readable UVW extraction is not yet in this repo (PDF source only);
the literature claim is recorded here for the addition ladder.
-/

namespace MatmulTensor.Smirnov84

def claimedAdditions : Nat := 84
theorem scheme_additions : claimedAdditions = 84 := rfl
def literatureNote : String :=
  "Smirnov 2013: rank 23, 84 naive additions; additive schedule not optimized in that paper."

end MatmulTensor.Smirnov84
