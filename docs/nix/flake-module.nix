{ inputs, self, ... }:
{
  perSystem =
    {
      config,
      self',
      pkgs,
      ...
    }:
    let
      # Simply evaluated options (JSON)
      # { clanCore = «derivation JSON»; clanModules = { ${name} = «derivation JSON» }; }
      jsonDocs = import ./get-module-docs.nix {
        inherit (inputs) nixpkgs;
        inherit pkgs self;
        inherit (self.nixosModules) clanCore;
        inherit (self) clanModules;
      };

      clanModulesFileInfo = pkgs.writeText "info.json" (builtins.toJSON jsonDocs.clanModules);
      clanModulesReadmes = pkgs.writeText "info.json" (builtins.toJSON jsonDocs.clanModulesReadmes);
      clanModulesMeta = pkgs.writeText "info.json" (builtins.toJSON jsonDocs.clanModulesMeta);

      # Simply evaluated options (JSON)
      renderOptions =
        pkgs.runCommand "renderOptions.py"
          {
            # TODO: ruff does not splice properly in nativeBuildInputs
            depsBuildBuild = [ pkgs.ruff ];
            nativeBuildInputs = [
              pkgs.python3
              pkgs.mypy
            ];
          }
          ''
            install ${./scripts/renderOptions.py} $out
            patchShebangs --build $out

            ruff format --check --diff $out
            ruff --line-length 88 $out
            mypy --strict $out
          '';

      asciinema-player-js = pkgs.fetchurl {
        url = "https://github.com/asciinema/asciinema-player/releases/download/v3.7.0/asciinema-player.min.js";
        sha256 = "sha256-Ymco/+FinDr5YOrV72ehclpp4amrczjo5EU3jfr/zxs=";
      };
      asciinema-player-css = pkgs.fetchurl {
        url = "https://github.com/asciinema/asciinema-player/releases/download/v3.7.0/asciinema-player.css";
        sha256 = "sha256-GZMeZFFGvP5GMqqh516mjJKfQaiJ6bL38bSYOXkaohc=";
      };

      module-docs = pkgs.runCommand "rendered" { nativeBuildInputs = [ pkgs.python3 ]; } ''
        export CLAN_CORE=${jsonDocs.clanCore}/share/doc/nixos/options.json
        # A file that contains the links to all clanModule docs
        export CLAN_MODULES=${clanModulesFileInfo}
        export CLAN_MODULES_READMES=${clanModulesReadmes}
        export CLAN_MODULES_META=${clanModulesMeta}

        mkdir $out

        # The python script will place mkDocs files in the output directory
        python3 ${renderOptions}
      '';
    in
    {
      devShells.docs = pkgs.callPackage ./shell.nix {
        inherit (self'.packages) docs clan-cli-docs;
        inherit module-docs;
        inherit asciinema-player-js;
        inherit asciinema-player-css;
      };
      packages = {
        docs = pkgs.python3.pkgs.callPackage ./default.nix {
          inherit (self'.packages) clan-cli-docs;
          inherit (inputs) nixpkgs;
          inherit module-docs;
          inherit asciinema-player-js;
          inherit asciinema-player-css;
        };
        deploy-docs = pkgs.callPackage ./deploy-docs.nix { inherit (config.packages) docs; };
        inherit module-docs;
      };
    };
}
