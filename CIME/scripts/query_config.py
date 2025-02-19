#!/usr/bin/env python3
"""
Displays information about available compsets, component settings, grids and/or
machines. Typically run with one of the arguments --compsets, --settings,
--grids or --machines; if you specify more than one of these arguments,
information will be listed for each.
"""

from CIME.Tools.standard_script_setup import *
import re
from CIME.utils import expect
from CIME.XML.files import Files
from CIME.XML.component import Component
from CIME.XML.compsets import Compsets
from CIME.XML.grids import Grids
from CIME.config import Config

# from CIME.XML.machines  import Machines
import CIME.XML.machines
from argparse import RawTextHelpFormatter

logger = logging.getLogger(__name__)

customize_path = os.path.join(CIME.utils.get_src_root(), "cime_config", "customize")

config = Config.load(customize_path)

supported_comp_interfaces = list(config.driver_choices)


def query_grids(files, long_output, xml=False):
    """
    query all grids.
    """
    config_file = files.get_value("GRIDS_SPEC_FILE")
    expect(
        os.path.isfile(config_file),
        "Cannot find config_file {} on disk".format(config_file),
    )

    grids = Grids(config_file)
    if xml:
        print("{}".format(grids.get_raw_record().decode("UTF-8")))
    elif long_output:
        grids.print_values(long_output=long_output)
    else:
        grids.print_values()


def query_machines(files, machine_name="all", xml=False):
    """
    query machines. Defaule: all
    """
    config_file = files.get_value("MACHINES_SPEC_FILE")
    expect(
        os.path.isfile(config_file),
        "Cannot find config_file {} on disk".format(config_file),
    )
    # Provide a special machine name indicating no need for a machine name
    machines = Machines(config_file, machine="Query")
    if xml:
        if machine_name == "all":
            print("{}".format(machines.get_raw_record().decode("UTF-8")))
        else:
            machines.set_machine(machine_name)
            print(
                "{}".format(
                    machines.get_raw_record(root=machines.machine_node).decode("UTF-8")
                )
            )
    else:
        machines.print_values(machine_name=machine_name)


def query_compsets(files, name, xml=False):
    """
    query compset definition give a compset name
    """
    # Determine valid component values by checking the value attributes for COMPSETS_SPEC_FILE
    components = get_compsets(files)
    match_found = None
    all_components = False
    if re.search("^all$", name):  # print all compsets
        match_found = name
        all_components = True
    else:
        for component in components:
            if component == name:
                match_found = name
                break

    # If name is not a valid argument - exit with error
    expect(
        match_found is not None,
        "Invalid input argument {}, valid input arguments are {}".format(
            name, components
        ),
    )

    if all_components:  # print all compsets
        for component in components:
            # the all_components flag will only print available components
            print_compset(component, files, all_components=all_components, xml=xml)
    else:
        print_compset(name, files, xml=xml)


def print_compset(name, files, all_components=False, xml=False):
    """
    print compsets associated with the component name, but if all_components is true only
    print the details if the associated component is available
    """

    # Determine the config_file for the target component
    config_file = files.get_value("COMPSETS_SPEC_FILE", attribute={"component": name})
    # only error out if we aren't printing all otherwise exit quitely
    if not all_components:
        expect(
            (config_file),
            "Cannot find any config_component.xml file for {}".format(name),
        )

        # Check that file exists on disk
        expect(
            os.path.isfile(config_file),
            "Cannot find config_file {} on disk".format(config_file),
        )
    elif config_file is None or not os.path.isfile(config_file):
        return

    if config.test_mode not in ("e3sm", "cesm") and name == "drv":
        return

    print("\nActive component: {}".format(name))
    # Now parse the compsets file and write out the compset alias and longname as well as the help text
    # determine component xml content
    compsets = Compsets(config_file)
    # print compsets associated with component without help text
    if xml:
        print("{}".format(compsets.get_raw_record().decode("UTF-8")))
    else:
        compsets.print_values(arg_help=False)


def query_all_components(files, xml=False):
    """
    query all components
    """
    components = get_components(files)
    # Loop through the elements for each component class (in config_files.xml)
    for comp in components:
        string = "CONFIG_{}_FILE".format(comp)

        # determine all components in string
        components = files.get_components(string)
        for item in components:
            query_component(item, files, all_components=True, xml=xml)


def query_component(name, files, all_components=False, xml=False):
    """
    query a component by name
    """
    # Determine the valid component classes (e.g. atm) for the driver/cpl
    # These are then stored in comps_array
    components = get_components(files)

    # Loop through the elements for each component class (in config_files.xml)
    # and see if there is a match for the the target component in the component attribute
    match_found = False
    valid_components = []
    config_exists = False
    for comp in components:
        string = "CONFIG_{}_FILE".format(comp)
        config_file = None
        # determine all components in string
        root_dir_node_name = "COMP_ROOT_DIR_{}".format(comp)
        components = files.get_components(root_dir_node_name)
        if components is None:
            components = files.get_components(string)
        for item in components:
            valid_components.append(item)
        logger.debug("{}: valid_components {}".format(comp, valid_components))
        # determine if config_file is on disk
        if name is None:
            config_file = files.get_value(string)
        elif name in valid_components:
            config_file = files.get_value(string, attribute={"component": name})
            logger.debug("query {}".format(config_file))
        if config_file is not None:
            match_found = True
            config_exists = os.path.isfile(config_file)
            break

    if not all_components and not config_exists:
        expect(config_exists, "Cannot find config_file {} on disk".format(config_file))
    elif all_components and not config_exists:
        print("WARNING: Couldn't find config_file {} on disk".format(config_file))
        return
    # If name is not a valid argument - exit with error
    expect(
        match_found,
        "Invalid input argument {}, valid input arguments are {}".format(
            name, valid_components
        ),
    )

    # Check that file exists on disk, if not exit with error
    expect(
        (config_file), "Cannot find any config_component.xml file for {}".format(name)
    )

    # determine component xml content
    component = Component(config_file, "CPL")
    if xml:
        print("{}".format(component.get_raw_record().decode("UTF-8")))
    else:
        component.print_values()


def parse_command_line(args, description):
    """
    parse command line arguments
    """
    cime_model = CIME.utils.get_model()

    parser = ArgumentParser(
        description=description, formatter_class=RawTextHelpFormatter
    )

    CIME.utils.setup_standard_logging_options(parser)

    valid_components = ["all"]

    parser.add_argument("--xml", action="store_true", help="Output in xml format.")

    files = {}
    for comp_interface in supported_comp_interfaces:
        files[comp_interface] = Files(comp_interface=comp_interface)
        components = files[comp_interface].get_components("COMPSETS_SPEC_FILE")
        for item in components:
            valid_components.append(item)

    parser.add_argument(
        "--compsets",
        nargs="?",
        const="all",
        choices=valid_components,
        help="Query compsets corresponding to the target component for the {} model."
        " If no component is given, lists compsets defined by all components".format(
            cime_model
        ),
    )

    # Loop through the elements for each component class (in config_files.xml)
    valid_components = ["all"]
    tmp_comp_interfaces = supported_comp_interfaces
    for comp_interface in tmp_comp_interfaces:
        try:
            components = get_components(files[comp_interface])
        except Exception:
            supported_comp_interfaces.remove(comp_interface)

        for comp in components:
            string = config.xml_component_key.format(comp)

            # determine all components in string
            components = files[comp_interface].get_components(string)
            if components:
                for item in components:
                    valid_components.append(item)

    parser.add_argument(
        "--components",
        nargs="?",
        const="all",
        choices=valid_components,
        help="Query component settings corresponding to the target component for {} model."
        "\nIf the option is empty, then the lists settings defined by all components is output".format(
            cime_model
        ),
    )

    parser.add_argument(
        "--grids",
        action="store_true",
        help="Query supported model grids for {} model.".format(cime_model),
    )
    # same for all comp_interfaces
    config_file = files["mct"].get_value("MACHINES_SPEC_FILE")
    expect(
        os.path.isfile(config_file),
        "Cannot find config_file {} on disk".format(config_file),
    )
    machines = Machines(config_file, machine="Query")
    machine_names = ["all", "current"]
    machine_names.extend(machines.list_available_machines())

    parser.add_argument(
        "--machines",
        nargs="?",
        const="all",
        choices=machine_names,
        help="Query supported machines for {} model."
        "\nIf option is left empty then all machines are listed,"
        "\nIf the option is 'current' then only the current machine details are listed.".format(
            cime_model
        ),
    )

    parser.add_argument(
        "--long", action="store_true", help="Provide long output for queries"
    )

    parser.add_argument(
        "--comp_interface",
        choices=supported_comp_interfaces,
        default="mct",
        help="Coupler/Driver interface",
    )

    args = CIME.utils.parse_args_and_handle_standard_logging_options(args, parser)

    # make sure at least one argument has been passed
    if not (args.grids or args.compsets or args.components or args.machines):
        parser.print_help(sys.stderr)

    return (
        args.grids,
        args.compsets,
        args.components,
        args.machines,
        args.long,
        args.xml,
        files[args.comp_interface],
    )


def get_compsets(files):
    """
    Determine valid component values by checking the value attributes for COMPSETS_SPEC_FILE
    """
    return files.get_components("COMPSETS_SPEC_FILE")


def get_components(files):
    """
    Determine the valid component classes (e.g. atm) for the driver/cpl
    These are then stored in comps_array
    """
    infile = files.get_value("CONFIG_CPL_FILE")
    config_drv = Component(infile, "CPL")
    return config_drv.get_valid_model_components()


class ArgumentParser(argparse.ArgumentParser):
    """
    we override the error message from ArgumentParser to have a more helpful
    message in the case of missing arguments
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        # missing argument
        # TODO: assumes comp_interface='mct'
        if "expected one argument" in message:
            if "compset" in message:
                components = get_compsets(Files(comp_interface="mct"))
                self.exit(
                    2,
                    "{}: error: {}\nValid input arguments are {}\n".format(
                        self.prog, message, components
                    ),
                )
            elif "component" in message:
                files = Files(comp_interface="mct")
                components = get_components(files)
                # Loop through the elements for each component class (in config_files.xml)
                valid_components = []
                for comp in components:
                    string = "CONFIG_{}_FILE".format(comp)

                    # determine all components in string
                    components = files.get_components(string)
                    for item in components:
                        valid_components.append(item)
                self.exit(
                    2,
                    "{}: error: {}\nValid input arguments are {}\n".format(
                        self.prog, message, valid_components
                    ),
                )
        # for all other errors
        self.exit(2, "{}: error: {}\n".format(self.prog, message))


class Machines(CIME.XML.machines.Machines):
    """
    we overide print_values from Machines to add current in machine description
    """

    def print_values(self, machine_name="all"):  # pylint: disable=arguments-differ
        # set flag to look for single machine
        if "all" not in machine_name:
            single_machine = True
            if machine_name == "current":
                machine_name = self.probe_machine_name(warn=False)
        else:
            single_machine = False

        # if we can't find the specified machine
        if single_machine and machine_name is None:
            files = Files()
            config_file = files.get_value("MACHINES_SPEC_FILE")
            print("Machine is not listed in config file: {}".format(config_file))
        else:  # write out machines
            if single_machine:
                machine_names = [machine_name]
            else:
                machine_names = self.list_available_machines()
            print("Machine(s)\n")
            for name in machine_names:
                self.set_machine(name)
                desc = self.text(self.get_child("DESC"))
                os_ = self.text(self.get_child("OS"))
                compilers = self.text(self.get_child("COMPILERS"))
                mpilibnodes = self.get_children("MPILIBS", root=self.machine_node)
                mpilibs = []
                for node in mpilibnodes:
                    mpilibs.extend(self.text(node).split(","))
                # This does not include the possible depedancy of mpilib on compiler
                # it simply provides a list of mpilibs available on the machine
                mpilibs = list(set(mpilibs))
                max_tasks_per_node = self.text(self.get_child("MAX_TASKS_PER_NODE"))
                mpitasks_node = self.get_optional_child(
                    "MAX_MPITASKS_PER_NODE", root=self.machine_node
                )
                max_mpitasks_per_node = (
                    self.text(mpitasks_node) if mpitasks_node else max_tasks_per_node
                )
                max_gpus_node = self.get_optional_child(
                    "MAX_GPUS_PER_NODE", root=self.machine_node
                )
                max_gpus_per_node = self.text(max_gpus_node) if max_gpus_node else 0

                current_machine = self.probe_machine_name(warn=False)
                name += (
                    " (current)" if current_machine and current_machine in name else ""
                )
                print("  {} : {} ".format(name, desc))
                print("      os             ", os_)
                print("      compilers      ", compilers)
                print("      mpilibs        ", mpilibs)
                if max_mpitasks_per_node is not None:
                    print("      pes/node       ", max_mpitasks_per_node)
                if max_tasks_per_node is not None:
                    print("      max_tasks/node ", max_tasks_per_node)
                if max_gpus_per_node is not None:
                    print("      max_gpus/node ", max_gpus_per_node)
                print("")


def _main_func(description=None):
    """
    main function
    """
    grids, compsets, components, machines, long_output, xml, files = parse_command_line(
        sys.argv, description
    )

    if grids:
        query_grids(files, long_output, xml=xml)

    if compsets is not None:
        query_compsets(files, name=compsets, xml=xml)

    if components is not None:
        if re.search("^all$", components):  # print all compsets
            query_all_components(files, xml=xml)
        else:
            query_component(components, files, xml=xml)

    if machines is not None:
        query_machines(files, machine_name=machines, xml=xml)


# main entry point
if __name__ == "__main__":
    _main_func(__doc__)
