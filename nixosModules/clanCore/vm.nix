{ lib, config, pkgs, options, extendModules, modulesPath, ... }:
let
  # Flatten the list of state folders into a single list
  stateFolders = lib.flatten (
    lib.mapAttrsToList
      (_item: attrs: attrs.folders)
      config.clanCore.state
  );


  vmModule = {
    imports = [
      (modulesPath + "/virtualisation/qemu-vm.nix")
      ./serial.nix
    ];

    # required for issuing shell commands via qga
    services.qemuGuest.enable = true;

    # required to react to system_powerdown qmp command
    # Some desktop managers like xfce override the poweroff signal and therefore
    #   make it impossible to handle it via 'logind' diretly.
    services.acpid.enable = true;
    services.acpid.handlers.power.event = "button/power.*";
    services.acpid.handlers.power.action = "poweroff";

    # only works on x11
    services.spice-vdagentd.enable = config.services.xserver.enable;

    boot.initrd.systemd.enable = true;

    # currently needed for system.etc.overlay.enable
    boot.kernelPackages = pkgs.linuxPackages_latest;

    boot.initrd.systemd.storePaths = [ pkgs.util-linux pkgs.e2fsprogs ];
    boot.initrd.systemd.emergencyAccess = true;

    # sysusers is faster than nixos's perl scripts
    # and doesn't require state.
    systemd.sysusers.enable = true;
    users.mutableUsers = false;
    users.allowNoPasswordLogin = true;

    boot.initrd.kernelModules = [ "virtiofs" ];
    virtualisation.writableStore = false;
    virtualisation.fileSystems = lib.mkForce ({
      "/nix/store" = {
        device = "nix-store";
        options = [ "x-systemd.requires=systemd-modules-load.service" "ro" ];
        fsType = "virtiofs";
      };

      "/" = {
        device = "/dev/vda";
        fsType = "ext4";
        options = [ "defaults" "x-systemd.makefs" "nobarrier" "noatime" "nodiratime" "data=writeback" "discard" ];
      };

      "/vmstate" = {
        device = "/dev/vdb";
        options = [ "x-systemd.makefs" "noatime" "nodiratime" "discard" ];
        noCheck = true;
        fsType = "ext4";
      };

      ${config.clanCore.secretsUploadDirectory} = {
        device = "secrets";
        fsType = "9p";
        neededForBoot = true;
        options = [ "trans=virtio" "version=9p2000.L" "cache=loose" ];
      };

    } // lib.listToAttrs (map
      (folder:
        lib.nameValuePair folder {
          device = "/vmstate${folder}";
          fsType = "none";
          options = [ "bind" ];
        })
      stateFolders));
  };

  # We cannot simply merge the VM config into the current system config, because
  # it is not necessarily a VM.
  # Instead we use extendModules to create a second instance of the current
  # system configuration, and then merge the VM config into that.
  vmConfig = extendModules {
    modules = [ vmModule ];
  };
in
{
  options = {
    clan.virtualisation = {
      cores = lib.mkOption {
        type = lib.types.ints.positive;
        default = 1;
        description = lib.mdDoc ''
          Specify the number of cores the guest is permitted to use.
          The number can be higher than the available cores on the
          host system.
        '';
      };

      memorySize = lib.mkOption {
        type = lib.types.ints.positive;
        default = 1024;
        description = lib.mdDoc ''
          The memory size in megabytes of the virtual machine.
        '';
      };

      graphics = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = lib.mdDoc ''
          Whether to run QEMU with a graphics window, or in nographic mode.
          Serial console will be enabled on both settings, but this will
          change the preferred console.
        '';
      };

      waypipe = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = lib.mdDoc ''
          Whether to use waypipe for native wayland passthrough, or not.
        '';
      };
    };
    # All important VM config variables needed by the vm runner
    # this is really just a remapping of values defined elsewhere
    # and therefore not intended to be set by the user
    clanCore.vm.inspect = {
      clan_name = lib.mkOption {
        type = lib.types.str;
        internal = true;
        readOnly = true;
        description = ''
          the name of the clan
        '';
      };
      memory_size = lib.mkOption {
        type = lib.types.int;
        internal = true;
        readOnly = true;
        description = ''
          the amount of memory to allocate to the vm
        '';
      };
      cores = lib.mkOption {
        type = lib.types.int;
        internal = true;
        readOnly = true;
        description = ''
          the number of cores to allocate to the vm
        '';
      };
      graphics = lib.mkOption {
        type = lib.types.bool;
        internal = true;
        readOnly = true;
        description = ''
          whether to enable graphics for the vm
        '';
      };
      waypipe = lib.mkOption {
        type = lib.types.bool;
        internal = true;
        readOnly = true;
        description = ''
          whether to enable native wayland window passthrough with waypipe for the vm
        '';
      };
      machine_icon = lib.mkOption {
        type = lib.types.nullOr lib.types.path;
        internal = true;
        readOnly = true;
        description = ''
          the location of the clan icon
        '';
      };
      machine_name = lib.mkOption {
        type = lib.types.str;
        internal = true;
        readOnly = true;
        description = ''
          the name of the vm
        '';
      };
      machine_description = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        internal = true;
        readOnly = true;
        description = ''
          the description of the vm
        '';
      };
    };
  };

  config = {
    # for clan vm inspect
    clanCore.vm.inspect = {
      clan_name = config.clanCore.clanName;
      machine_icon = config.clanCore.machineIcon or config.clanCore.clanIcon;
      machine_name = config.clanCore.machineName;
      machine_description = config.clanCore.machineDescription;
      memory_size = config.clan.virtualisation.memorySize;
      inherit (config.clan.virtualisation) cores graphics waypipe;
    };
    # for clan vm create
    system.clan.vm = {
      create = pkgs.writeText "vm.json" (builtins.toJSON {
        initrd = "${vmConfig.config.system.build.initialRamdisk}/${vmConfig.config.system.boot.loader.initrdFile}";
        toplevel = vmConfig.config.system.build.toplevel;
        regInfo = (pkgs.closureInfo { rootPaths = vmConfig.config.virtualisation.additionalPaths; });
        inherit (config.clan.virtualisation) memorySize cores graphics;
      });
    };

    virtualisation = lib.optionalAttrs (options.virtualisation ? cores) {
      memorySize = lib.mkDefault config.clan.virtualisation.memorySize;
      graphics = lib.mkDefault config.clan.virtualisation.graphics;
      cores = lib.mkDefault config.clan.virtualisation.cores;
    };
  };
}
