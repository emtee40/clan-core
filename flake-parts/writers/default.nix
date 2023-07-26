{ flake-parts-lib, ... }: {
  options.perSystem = flake-parts-lib.mkPerSystemOption (
    { config
    , lib
    , pkgs
    , ...
    }:
    let
      writers = pkgs.callPackage ./writers.nix { };
    in
    {
      options.writers = {
        writePureShellScript = lib.mkOption {
          type = lib.types.functionTo (lib.types.functionTo lib.types.package);
          description = ''
            Create a script that runs in a `pure` environment, in the sense that:
              - the behavior is similar to `nix-shell --pure`
              - `PATH` only contains exactly the packages passed via the `PATH` arg
              - `NIX_PATH` is set to the path of the current `pkgs`
              - `TMPDIR` is set up and cleaned up even if the script fails
              - out, if set, is kept as-is
              - all environment variables are unset, except:
                - the ones listed in `keepVars` defined in ./default.nix
                - the ones listed via the `KEEP_VARS` variable
          '';
        };
        writePureShellScriptBin = lib.mkOption {
          type = lib.types.functionTo (lib.types.functionTo (lib.types.functionTo lib.types.package));
          description = ''
            Creates a script in a `bin/` directory in the output; suitable for use with `lib.makeBinPath`, etc.
            See {option}`writers.writePureShellScript`
          '';
        };
      };

      config.writers = {
        inherit
          (writers)
          writePureShellScript
          writePureShellScriptBin
          ;
      };
    }
  );
}
