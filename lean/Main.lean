import MatmulTensor

def main : IO Unit := do
  let schemes := [
    ("Laderman", MatmulTensor.brentOK MatmulTensor.Laderman.scheme, MatmulTensor.Laderman.scheme.rank, MatmulTensor.Laderman.scheme.support, MatmulTensor.Laderman.claimedAdditions),
    ("Stapleton60", MatmulTensor.brentOK MatmulTensor.Stapleton60.scheme, MatmulTensor.Stapleton60.scheme.rank, MatmulTensor.Stapleton60.scheme.support, MatmulTensor.Stapleton60.claimedAdditions),
    ("Perminov58", MatmulTensor.brentOK MatmulTensor.Perminov58.scheme, MatmulTensor.Perminov58.scheme.rank, MatmulTensor.Perminov58.scheme.support, MatmulTensor.Perminov58.claimedAdditions),
    ("Sun56", MatmulTensor.brentOK MatmulTensor.Sun56.scheme, MatmulTensor.Sun56.scheme.rank, MatmulTensor.Sun56.scheme.support, MatmulTensor.Sun56.claimedAdditions),
  ]
  for (n,b,r,s,a) in schemes do
    IO.println s!"{n}: brent={b} rank={r} support={s} claimedAdd={a}"
  IO.println s!"Smirnov literature claim: {MatmulTensor.Smirnov84.claimedAdditions} additions"
  IO.println s!"Martensson literature claim: {MatmulTensor.Martensson59.claimedAdditions} additions"
