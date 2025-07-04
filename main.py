from Lib.Classes import Logger
from Lib.Classes import Vars
from Lib.Classes import Netbox
from pprint import pprint as pp

# Initialize Logger
log = Logger().get_logger()

# Intialize input vars
input_file = "Var/input.yml"
input_vars = Vars(input_file).get_vars()

def main():
    with Netbox(**input_vars) as input_struct:
        input_struct.orchestrate_output_file_creation()

if __name__ == "__main__":
    main()