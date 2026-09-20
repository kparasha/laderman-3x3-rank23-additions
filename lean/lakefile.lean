import Lake
open Lake DSL

package «matmul-tensor» where
  version := v!"0.1.0"

lean_lib MatmulTensor where
  globs := #[.andSubmodules `MatmulTensor]

@[default_target]
lean_exe matmul_tensor where
  root := `Main
