{ config, lib, ... }:
{
  options.clan.disk-layouts.singleDiskExt4 = {
    device = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      example = "/dev/disk/by-id/ata-Samsung_SSD_850_EVO_250GB_S21PNXAGB12345";
      default = null;
    };
  };
  config = {
    boot.loader.grub.efiSupport = lib.mkDefault true;
    boot.loader.grub.efiInstallAsRemovable = lib.mkDefault true;
    disko.devices = {
      disk = {
        main = {
          type = "disk";
          device = config.clan.disk-layouts.singleDiskExt4.device;
          content = {
            device = lib.mkDefault config.clan.diskLayouts.singleDiskExt4.device;
            type = "gpt";
            partitions = {
              boot = {
                size = "1M";
                type = "EF02"; # for grub MBR
              };
              ESP = {
                size = "512M";
                type = "EF00";
                content = {
                  type = "filesystem";
                  format = "vfat";
                  mountpoint = "/boot";
                };
              };
              root = {
                size = "100%";
                content = {
                  type = "filesystem";
                  format = "ext4";
                  mountpoint = "/";
                };
              };
            };
          };
        };
      };
    };
  };
}
