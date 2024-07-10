import { currClanURI } from "../App";

export const Header = () => {
  return (
    <div class="navbar bg-base-100">
      <div class="flex-none">
        <span class="tooltip tooltip-bottom" data-tip="Menu">
          <label
            class="btn btn-square btn-ghost drawer-button"
            for="toplevel-drawer"
          >
            <span class="material-icons">menu</span>
          </label>
        </span>
      </div>
      <div class="flex-1">
        <a class="text-xl">{currClanURI() || "Clan"}</a>
      </div>
      <div class="flex-none">
        <span class="tooltip tooltip-bottom" data-tip="Account">
          <button class="btn btn-square btn-ghost">
            <span class="material-icons">account_circle</span>
          </button>
        </span>
      </div>
    </div>
  );
};
