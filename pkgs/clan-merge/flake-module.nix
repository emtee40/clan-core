{
  perSystem = { pkgs, ... }:
    let
      package = pkgs.callPackage ./default.nix { };
    in
    {
      packages.clan-merge = package;
      checks.clan-merge = package.tests.check;
    };
}
