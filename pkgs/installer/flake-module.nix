{ self, lib, ... }:

let
  wifiModule =
    { ... }:
    {
      # use iwd instead of wpa_supplicant
      networking.wireless.enable = false;

      # Use iwd instead of wpa_supplicant. It has a user friendly CLI
      networking.wireless.iwd = {
        enable = true;
        settings = {
          Network = {
            EnableIPv6 = true;
            RoutePriorityOffset = 300;
          };
          Settings.AutoConnect = true;
        };
      };
    };
  installerModule =
    {
      config,
      pkgs,
      modulesPath,
      ...
    }:
    {
      imports = [
        wifiModule
        self.nixosModules.installer
        self.inputs.nixos-generators.nixosModules.all-formats
        self.inputs.disko.nixosModules.disko
        (modulesPath + "/installer/cd-dvd/iso-image.nix")
      ];

      isoImage.squashfsCompression = "zstd";

      system.stateVersion = config.system.nixos.version;
      nixpkgs.pkgs = self.inputs.nixpkgs.legacyPackages.x86_64-linux;
    };

  installerSystem = lib.nixosSystem {
    modules = [
      installerModule
      { disko.memSize = 4096; } # FIXME: otherwise the image builder goes OOM
    ];
  };

  flashInstallerModule =
    { config, pkgs, ... }:
    {
      imports = [
        wifiModule
        self.nixosModules.installer
        self.clanModules.diskLayouts
      ];
      system.stateVersion = config.system.nixos.version;
      nixpkgs.pkgs = self.inputs.nixpkgs.legacyPackages.x86_64-linux;
    };
in
{
  clan = {
    clanName = "clan-core";
    directory = self;

    # To build a generic installer image (without ssh pubkeys),
    # use the following command:
    # $ nix build .#iso-installer
    machines.iso-installer = {
      imports = [ installerModule ];
      fileSystems."/".device = lib.mkDefault "/dev/null";
    };

    # To directly flash the installer to a disk, use the following command:
    # $ clan flash flash-installer --disk main /dev/sdX --yes
    # This will include your ssh public keys in the installer.
    machines.flash-installer = {
      imports = [ flashInstallerModule ];
      clan.diskLayouts.singleDiskExt4.device = lib.mkDefault "/dev/null";
      boot.loader.grub.enable = lib.mkDefault true;
    };
  };
  flake.packages.x86_64-linux.iso-installer = installerSystem.config.formats.iso;
  flake.apps.x86_64-linux.install-vm.program = installerSystem.config.formats.vm.outPath;
  flake.apps.x86_64-linux.install-vm-nogui.program = installerSystem.config.formats.vm-nogui.outPath;
}
