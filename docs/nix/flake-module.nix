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

      module-docs = pkgs.runCommand "rendered" { nativeBuildInputs = [ pkgs.python3 ]; } ''
        export CLAN_CORE=${jsonDocs.clanCore}/share/doc/nixos/options.json 
        # A file that contains the links to all clanModule docs
        export CLAN_MODULES=${clanModulesFileInfo}
        export CLAN_MODULES_READMES=${clanModulesReadmes}

        mkdir $out

        # The python script will place mkDocs files in the output directory
        python3 ${renderOptions}
      '';
    in
    {
      devShells.docs = pkgs.callPackage ./shell.nix {
        inherit (self'.packages) docs;
        inherit module-docs;
      };
      packages = {
        docs = pkgs.python3.pkgs.callPackage ./default.nix {
          inherit (inputs) nixpkgs;
          inherit module-docs;
        };
        deploy-docs = pkgs.callPackage ./deploy-docs.nix { inherit (config.packages) docs; };
        inherit module-docs;
      };
      legacyPackages = {
        foo = jsonDocs;
      };
    };
}
