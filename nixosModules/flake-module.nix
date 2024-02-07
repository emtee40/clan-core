{ inputs, self, ... }: {
  flake.nixosModules = {
    hidden-ssh-announce.imports = [ ./hidden-ssh-announce.nix ];
    installer.imports = [ ./installer ];
    clanCore.imports = [
      inputs.sops-nix.nixosModules.sops
      inputs.disko.nixosModules.disko # TODO use this only where we need it
      ./clanCore
      ./iso
      ({ pkgs, lib, ... }: {
        clanCore.clanPkgs = lib.mkDefault self.packages.${pkgs.hostPlatform.system};
      })
    ];
  };
}
