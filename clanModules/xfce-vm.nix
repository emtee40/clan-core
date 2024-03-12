{
  services.xserver = {
    enable = true;
    displayManager.autoLogin.enable = true;
    displayManager.autoLogin.user = "user";
    desktopManager.xfce.enable = true;
    desktopManager.xfce.enableScreensaver = false;
    xkb.layout = "us";
  };
  services.spice-vdagentd.enable = true;

  fonts.enableDefaultPackages = true;

  security = {
    sudo.wheelNeedsPassword = false;
    polkit.enable = true;
    rtkit.enable = true;
  };

  users.users.user = {
    isNormalUser = true;
    createHome = true;
    uid = 1000;
    initialHashedPassword = "";
    extraGroups = [
      "wheel"
      "video"
      "render"
    ];
    shell = "/run/current-system/sw/bin/bash";
  };

}
