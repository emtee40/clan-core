{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.clan.matrix-synapse;
  nginx-vhost = "matrix.${config.clan.matrix-synapse.domain}";
  element-web =
    pkgs.runCommand "element-web-with-config" { nativeBuildInputs = [ pkgs.buildPackages.jq ]; }
      ''
        cp -r ${pkgs.element-web} $out
        chmod -R u+w $out
        jq '."default_server_config"."m.homeserver" = { "base_url": "https://${nginx-vhost}:443", "server_name": "${config.clan.matrix-synapse.domain}" }' \
          > $out/config.json < ${pkgs.element-web}/config.json
        ln -s $out/config.json $out/config.${nginx-vhost}.json
      '';

  # FIXME: This was taken from upstream. Drop this when our patch is upstream
  synapseCfg = config.services.matrix-synapse;
  wantedExtras =
    synapseCfg.extras
    ++ lib.optional (synapseCfg.settings ? oidc_providers) "oidc"
    ++ lib.optional (synapseCfg.settings ? jwt_config) "jwt"
    ++ lib.optional (synapseCfg.settings ? saml2_config) "saml2"
    ++ lib.optional (synapseCfg.settings ? redis) "redis"
    ++ lib.optional (synapseCfg.settings ? sentry) "sentry"
    ++ lib.optional (synapseCfg.settings ? user_directory) "user-search"
    ++ lib.optional (synapseCfg.settings.url_preview_enabled) "url-preview"
    ++ lib.optional (synapseCfg.settings.database.name == "psycopg2") "postgres";

in
{
  options.services.matrix-synapse.package = lib.mkOption { readOnly = false; };
  options.clan.matrix-synapse = {
    domain = lib.mkOption {
      type = lib.types.str;
      description = "The domain name of the matrix server";
      example = "example.com";
    };
    users = lib.mkOption {
      default = { };
      type = lib.types.attrsOf (
        lib.types.submodule (
          { name, ... }:
          {
            options = {
              name = lib.mkOption {
                type = lib.types.str;
                default = name;
                description = "The name of the user";
              };

              admin = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Whether the user should be an admin";
              };
            };
          }
        )
      );
      description = "A list of users. Not that only new users will be created and existing ones are not modified.";
      example.alice = {
        admin = true;
      };
    };
  };
  imports = [
    ../postgresql
    (lib.mkRemovedOptionModule [
      "clan"
      "matrix-synapse"
      "enable"
    ] "Importing the module will already enable the service.")

    ../postgresql
  ];
  config = {
    services.matrix-synapse = {
      package = lib.mkForce (
        pkgs.matrix-synapse.override {
          matrix-synapse-unwrapped = pkgs.matrix-synapse.unwrapped.overrideAttrs (_old: {
            doInstallCheck = false; # too slow, nixpkgs maintainer already run this.
            # see: https://github.com/element-hq/synapse/pull/17294
            patches = [ ./0001-register_new_matrix_user-add-password-file-flag.patch ];
          });
          extras = wantedExtras;
          plugins = synapseCfg.plugins;
        }
      );

      enable = true;
      settings = {
        server_name = cfg.domain;
        database = {
          args.user = "matrix-synapse";
          args.database = "matrix-synapse";
          name = "psycopg2";
        };
        turn_uris = [
          "turn:turn.matrix.org?transport=udp"
          "turn:turn.matrix.org?transport=tcp"
        ];
        listeners = [
          {
            port = 8008;
            bind_addresses = [ "::1" ];
            type = "http";
            tls = false;
            x_forwarded = true;
            resources = [
              {
                names = [ "client" ];
                compress = true;
              }
              {
                names = [ "federation" ];
                compress = false;
              }
            ];
          }
        ];
      };
      extraConfigFiles = [ "/run/synapse-registration-shared-secret.yaml" ];
    };

    systemd.tmpfiles.settings."01-matrix" = {
      "/run/synapse-registration-shared-secret.yaml" = {
        C.argument =
          config.clanCore.facts.services.matrix-synapse.secret.synapse-registration_shared_secret.path;
        z = {
          mode = "0400";
          user = "matrix-synapse";
        };
      };
    };

    clan.postgresql.users.matrix-synapse = { };
    clan.postgresql.databases.matrix-synapse.create.options = {
      TEMPLATE = "template0";
      LC_COLLATE = "C";
      LC_CTYPE = "C";
      ENCODING = "UTF8";
      OWNER = "matrix-synapse";
    };

    clanCore.facts.services =
      {
        "matrix-synapse" = {
          secret."synapse-registration_shared_secret" = { };
          generator.path = with pkgs; [
            coreutils
            pwgen
          ];
          generator.script = ''
            echo "registration_shared_secret: $(pwgen -s 32 1)" > "$secrets"/synapse-registration_shared_secret
          '';
        };
      }
      // lib.mapAttrs' (
        name: user:
        lib.nameValuePair "matrix-password-${user.name}" {
          secret."matrix-password-${user.name}" = { };
          generator.path = with pkgs; [
            coreutils
            pwgen
          ];
          generator.script = ''
            xkcdpass -n 4 -d - > "$secrets"/${lib.escapeShellArg "matrix-password-${user.name}"}
          '';
        }
      ) cfg.users;

    systemd.services.matrix-synapse =
      let
        usersScript =
          ''
            while ! ${pkgs.netcat}/bin/nc -z -v ::1 8008; do
              if ! kill -0 "$MAINPID"; then exit 1; fi
              sleep 1;
            done

            headers=$(mktemp)
            trap 'rm -f "$headers"' EXIT

            cat > "$headers" <<EOF
            Authorization: Bearer $(cat /run/synapse-registration-shared-secret.yaml| sed -n 's/registration_shared_secret: //p')
            EOF
          ''
          + lib.concatMapStringsSep "\n" (user: ''
            # only create user if it doesn't exist
            if ! curl --header "$headers" "http://localhost:8008/_synapse/admin/v1/whois/${user.name}@${cfg.domain}" >&2; then
              /run/current-system/sw/bin/matrix-synapse-register_new_matrix_user --password-file ${
                config.clanCore.facts.services."matrix-password-${user.name}".secret."matrix-password-${user.name}".path
              } --user "${user.name}" ${if user.admin then "--admin" else "--no-admin"}
            fi
          '') (lib.attrValues cfg.users);
      in
      {
        path = [ pkgs.curl ];
        serviceConfig.ExecStartPost = [
          (''+${pkgs.writeShellScript "matrix-synapse-create-users" usersScript}'')
        ];
      };

    services.nginx = {
      enable = true;
      virtualHosts = {
        ${cfg.domain} = {
          locations."= /.well-known/matrix/server".extraConfig = ''
            add_header Content-Type application/json;
            return 200 '${builtins.toJSON { "m.server" = "matrix.${cfg.domain}:443"; }}';
          '';
          locations."= /.well-known/matrix/client".extraConfig = ''
            add_header Content-Type application/json;
            add_header Access-Control-Allow-Origin *;
            return 200 '${
              builtins.toJSON {
                "m.homeserver" = {
                  "base_url" = "https://${nginx-vhost}";
                };
                "m.identity_server" = {
                  "base_url" = "https://vector.im";
                };
              }
            }';
          '';
        };
        ${nginx-vhost} = {
          forceSSL = true;
          enableACME = true;
          locations."/_matrix".proxyPass = "http://localhost:8008";
          locations."/_synapse".proxyPass = "http://localhost:8008";
          locations."/".root = element-web;
        };
      };
    };
  };
}
