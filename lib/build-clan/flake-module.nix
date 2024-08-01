{ self, inputs, ... }:
let
  inputOverrides = builtins.concatStringsSep " " (
    builtins.map (input: " --override-input ${input} ${inputs.${input}}") (builtins.attrNames inputs)
  );
in
{

  perSystem =
    {
      pkgs,
      lib,
      system,
      ...
    }:
    # let

    # in
    {

      # Run: nix-unit --extra-experimental-features flakes --flake .#legacyPackages.x86_64-linux.evalTests
      legacyPackages.evalTests-build-clan = import ./tests.nix {
        inherit lib;
        inherit (inputs) nixpkgs;
        clan-core = self;
        buildClan = self.lib.buildClan;
      };
      checks = {
        lib-build-clan-eval = pkgs.runCommand "tests" { nativeBuildInputs = [ pkgs.nix-unit ]; } ''
          export HOME="$(realpath .)"

          nix-unit --eval-store "$HOME" \
            --extra-experimental-features flakes \
            ${inputOverrides} \
            --flake ${self}#legacyPackages.${system}.evalTests-build-clan

          touch $out
        '';
      };
    };
}
