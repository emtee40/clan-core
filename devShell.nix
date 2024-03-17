{
  perSystem =
    { pkgs
    , self'
    , config
    , ...
    }:
    let
      writers = pkgs.callPackage ./pkgs/builders/script-writers.nix { };

      ansiEscapes = {
        reset = ''\033[0m'';
        green = ''\033[32m'';
      };

      # A python program to switch between dev-shells
      # usage: select-shell shell-name
      # the currently enabled dev-shell gets stored in ./.direnv/selected-shell
      select-shell = writers.writePython3Bin "select-shell"
        {
          flakeIgnore = [ "E501" ];
        } ./pkgs/scripts/select-shell.py;
    in
    {
      devShells.default = pkgs.mkShell {
        packages = [
          select-shell
          pkgs.tea
          pkgs.nix
          self'.packages.tea-create-pr
          self'.packages.merge-after-ci
          self'.packages.pending-reviews
          # treefmt with config defined in ./flake-parts/formatting.nix
          config.treefmt.build.wrapper
        ];
        shellHook = ''
          # no longer used
          rm -f "$(git rev-parse --show-toplevel)/.git/hooks/pre-commit"

          echo -e "${ansiEscapes.green}switch to another dev-shell using: select-shell${ansiEscapes.reset}"
        '';
      };
    };
}
