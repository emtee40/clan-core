{ lib
, inputs
, ...
}: {
  imports = [
    inputs.treefmt-nix.flakeModule
  ];
  perSystem = { self', pkgs, ... }: {
    treefmt.projectRootFile = "flake.nix";
    treefmt.flakeCheck = true;
    treefmt.flakeFormatter = true;
    treefmt.programs.shellcheck.enable = true;

    treefmt.programs.deno.enable = true;
    treefmt.settings.formatter.deno.excludes = [
      "secrets.yaml"
      "key.json"
    ];

    treefmt.programs.mypy.enable = true;
    treefmt.programs.mypy.directories = {
      "pkgs/clan-cli".extraPythonPackages = self'.packages.clan-cli.testDependencies;
    };

    treefmt.settings.formatter.nix = {
      command = "sh";
      options = [
        "-eucx"
        ''
          # First deadnix
          ${lib.getExe pkgs.deadnix} --edit "$@"
          # Then nixpkgs-fmt
          ${lib.getExe pkgs.nixpkgs-fmt} "$@"
        ''
        "--" # this argument is ignored by bash
      ];
      includes = [ "*.nix" ];
    };
    treefmt.settings.formatter.python = {
      command = "sh";
      options = [
        "-eucx"
        ''
          ${lib.getExe pkgs.ruff} --fix "$@"
          ${lib.getExe pkgs.black} "$@"
        ''
        "--" # this argument is ignored by bash
      ];
      includes = [ "*.py" ];
    };
  };
}
