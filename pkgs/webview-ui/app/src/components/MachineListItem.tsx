import { createSignal, Match, Show, Switch } from "solid-js";
import { ErrorData, pyApi, SuccessData } from "../api";
import { currClanURI } from "../App";

type MachineDetails = SuccessData<"list_machines">["data"][string];

interface MachineListItemProps {
  name: string;
  info: MachineDetails;
}

type HWInfo = Record<string, SuccessData<"show_machine_hardware_info">["data"]>;
type DeploymentInfo = Record<
  string,
  SuccessData<"show_machine_deployment_target">["data"]
>;

type MachineErrors = Record<string, ErrorData<"show_machine">["errors"]>;

const [hwInfo, setHwInfo] = createSignal<HWInfo>({});

const [deploymentInfo, setDeploymentInfo] = createSignal<DeploymentInfo>({});

const [errors, setErrors] = createSignal<MachineErrors>({});

pyApi.show_machine_hardware_info.receive((r) => {
  const { op_key } = r;
  if (r.status === "error") {
    console.error(r.errors);
    if (op_key) {
      setHwInfo((d) => ({ ...d, [op_key]: { system: null } }));
    }
    return;
  }
  if (op_key) {
    setHwInfo((d) => ({ ...d, [op_key]: r.data }));
  }
});

pyApi.show_machine_deployment_target.receive((r) => {
  const { op_key } = r;
  if (r.status === "error") {
    console.error(r.errors);
    if (op_key) {
      setDeploymentInfo((d) => ({ ...d, [op_key]: null }));
    }
    return;
  }
  if (op_key) {
    setDeploymentInfo((d) => ({ ...d, [op_key]: r.data }));
  }
});

export const MachineListItem = (props: MachineListItemProps) => {
  const { name, info } = props;

  pyApi.show_machine_hardware_info.dispatch({
    op_key: name,
    clan_dir: currClanURI(),
    machine_name: name,
  });

  pyApi.show_machine_deployment_target.dispatch({
    op_key: name,
    clan_dir: currClanURI(),
    machine_name: name,
  });

  return (
    <li>
      <div class="card card-side m-2 bg-base-100 shadow-lg">
        <figure class="pl-2">
          <span class="material-icons content-center text-5xl">
            devices_other
          </span>
        </figure>
        <div class="card-body flex-row justify-between">
          <div class="flex flex-col">
            <h2 class="card-title">{name}</h2>
            <div class="text-slate-600">
              <Show
                when={info}
                fallback={
                  <Switch fallback={<div class="skeleton h-8 w-full"></div>}>
                    <Match when={!info.description}>No description</Match>
                  </Switch>
                }
              >
                {(d) => d()?.description}
              </Show>
            </div>
            <div class="flex flex-row flex-wrap gap-4 py-2">
              <div class="badge badge-primary flex flex-row gap-1 py-4 align-middle">
                <span class="material-icons">
                  {hwInfo()[name]?.system ? "check" : "pending"}
                </span>

                <Switch fallback={<div class="skeleton h-8 w-full"></div>}>
                  <Match when={hwInfo()[name]?.system}>
                    {(system) => "System: " + system()}
                  </Match>
                  <Match when={hwInfo()[name]?.system === null}>
                    {"No hardware info"}
                  </Match>
                </Switch>
              </div>

              <div class="badge badge-primary flex flex-row gap-1 py-4 align-middle">
                <span class="material-icons">
                  {deploymentInfo()[name] ? "check" : "pending"}
                </span>
                <Show
                  when={deploymentInfo()[name]}
                  fallback={
                    <Switch fallback={<div class="skeleton h-8 w-full"></div>}>
                      <Match when={deploymentInfo()[name] !== undefined}>
                        No deployment target detected
                      </Match>
                    </Switch>
                  }
                >
                  {(i) => "Deploys to: " + i()}
                </Show>
              </div>
            </div>
            {/* Show only the first error at the bottom */}
            <Show when={errors()[name]?.[0]}>
              {(error) => (
                <div class="badge badge-error py-4">
                  Error: {error().message}: {error().description}
                </div>
              )}
            </Show>
          </div>
          <div>
            <button class="btn btn-ghost">
              <span class="material-icons">more_vert</span>
            </button>
          </div>
        </div>
      </div>
    </li>
  );
};
