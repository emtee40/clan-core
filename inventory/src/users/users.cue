package users

#user: users: [string]: {
   "autoInclude": bool,
   // TODO: this can include all available user-schemas
   "schemas": [ "ssh-user" ],
   "config": {
     ...
   }
}