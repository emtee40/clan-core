{ ... }:
{
  flake.clanModules = {
    disk-layouts = {
      imports = [ ./disk-layouts ];
    };
    borgbackup = ./borgbackup;
    borgbackup-static = ./borgbackup-static;
    deltachat = ./deltachat;
    ergochat = ./ergochat;
    localbackup = ./localbackup;
    localsend = ./localsend;
    matrix-synapse = ./matrix-synapse;
    moonlight = ./moonlight;
    root-password = ./root-password;
    sshd = ./sshd;
    sunshine = ./sunshine;
    static-hosts = ./static-hosts;
    syncthing = ./syncthing;
    thelounge = ./thelounge;
    trusted-nix-caches = ./trusted-nix-caches;
    user-password = ./user-password;
    xfce = ./xfce;
    zerotier-static-peers = ./zerotier-static-peers;
    zt-tcp-relay = ./zt-tcp-relay;
  };
}
