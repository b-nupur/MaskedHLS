import re
import sys
class TestBenchGenerator:
    """
    A class to generator verilog testbench for verilog module
    """
    def __init__(self, verilog_file, module_name, clock_period):
        """
        Initialize the object with verilog file to process.
        """
        self.verilog_file = verilog_file
        self.module_name = module_name
        self.module_clock = clock_period
        self.reg_signals = []
        self.wire_signals = []
        self.clk_signal = None
        self.shares = None

    def parse_verilog_module(self):
        # read the entire content of the file in verilog_code
        with open(self.verilog_file,'r') as file:
            verilog_code = file.read()

        # extract the module name and its port list
        module_reg = re.search(rf'module\s+{self.module_name}\s*\((.*?)\);', verilog_code, re.MULTILINE | re.DOTALL)
        # print(f"module name extracted {module_reg}")
        if not module_reg:
            print(f"Error: Module '{self.module_name}' not found in the Verilog file.")
            sys.exit(1)
        ports = [port.strip() for port in module_reg.group(1).split(',')]
        # print(f"ports: {ports}")

        # extract the individual port details 
        module_start = verilog_code.find(module_reg.group(0))
        module_body = verilog_code[module_start:]
        # remove leadinga and trailing spaces from the port name 
            
            # regex:
            #       input|output|inout : matches the port direction 
            #       \s+(wire|reg)? : optionally matches wire and reg keyword
            #       \s*(\[.*?\])? : optionally mataches bus width declaration like [7:0]
            #       \s*(\w+) : Captures the port name

        for match in re.finditer(rf'(input|output|inout)\s+(wire|reg)?\s*(\[.*?\])?\s*(\w+)', module_body, re.MULTILINE):
            
            direction = match.group(1)
            signal_type = match.group(2)
            name = match.group(4)
            # if name.lower() == "clk":
            #     self.clk_signal = name
            if name in ports:
                if direction == 'input':
                    self.reg_signals.append(name)
                else:
                    self.wire_signals.append(name)
        
        
    def generate_testbench(self):
        """Generate a Verilog testbench based on the extracted module information."""
        tb_name = f"{self.module_name}_tb"
        testbench = [f"module {tb_name};\n"]
        
        # Declare signals for testbench
        # Declare signals for testbench in groups
        # if self.clk_signal:
        #     testbench.append(f"\treg {self.clk_signal};")
        if self.reg_signals:
            testbench.append(f"\treg {', '.join(self.reg_signals)};")
        if self.wire_signals:
            testbench.append(f"\twire {', '.join(self.wire_signals)};")
        
        testbench.append("")


        # Instantiate the module under test (MUT)
        testbench.append(f"\t{self.module_name} uut (")
        testbench.append(',\n'.join([f"\t\t.{name}({name})" for name in self.reg_signals + self.wire_signals]))
        testbench.append("\t);\n")

        testbench.append(f"\talways #{self.module_clock} clk = ~clk")

        # create initial block for test 
        testbench.append("\tinitial begin")
        testbench.append("\t\t// Initialize all inputs")

        
        for name in self.reg_signals:
            testbench.append(f"\t\t{name} = 0;")
            if name == "r":
                testbench.append(f"\t\t{name} = $random")

        # add $display statment in  include the input signal and output signal and combining the share of x0 x1,x2, x3 and y0, y1, y2, y3 
         # Add $display statement to include input and output signals
        number_suffixes = {int(name.rsplit('_', 1)[1]) for name in self.reg_signals if '_' in name}

        # print(f"number sufix : {number_suffixes}")
        self.shares = max(number_suffixes)+1 if number_suffixes else None
        # print(f"number shares = {self.shares}")
        # Add $display statement to include only signals ending with _{number}
        testbench.append("\t\t// Display input and output signals")
        numbered_signals_x = sorted(set([re.sub(r'_\d+$', '', name) for name in self.reg_signals if re.search(r'_\d+$', name)]), reverse=True)
        numbered_signals_y = sorted(set([re.sub(r'_\d+$', '', name) for name in self.wire_signals if re.search(r'_\d+$', name)]), reverse=True)
        if numbered_signals_x:
            testbench.append(f"\t\t$display(\"{', '.join(numbered_signals_x)} | {', '.join(numbered_signals_y)}\");")

        # add test all combination of inputs
        # Add nested loops for all shares
        testbench.append("\t\t// Test all combinations of inputs")
        loop_vars = [f"i{idx}" for idx in range(self.shares)]
        for idx, var in enumerate(loop_vars):
            indent = "\t" * (idx + 2)
            testbench.append(f"{indent}for (integer {var} = 0; {var} < 16; {var} = {var} + 1) begin")
            share_signals = [name for name in self.reg_signals if f"_{idx}" in name]
            if share_signals:
                testbench.append(f"{indent}\t{{ {', '.join(share_signals)} }} = {var};")
        testbench.append("\t\t" + "\t" * self.shares + "#20;")
        testbench.append("\t\t" + "\t" * self.shares + "$display(\"%b  %b  %b  %b |  %b  %b  %b  %b\", ")
        testbench.append("\t\t" + "\t" * self.shares + "x3_0 ^ x3_1 ^ x3_2, x2_0 ^ x2_1 ^ x2_2, x1_0 ^ x1_1 ^ x1_2, x0_0 ^ x0_1 ^ x0_2,")
        testbench.append("\t\t" + "\t" * self.shares + "y3_0 ^ y3_1 ^ y3_2, y2_0 ^ y2_1 ^ y2_2, y1_0 ^ y1_1 ^ y1_2, y0_0 ^ y0_1 ^ y0_2);")
        testbench.append("")
        for i in range(self.shares-1,-1,-1):
            testbench.append("\t" * (i+2) + "end")

        testbench.append("")
        
       
        testbench.append("\t\t$finish")
        testbench.append("\tend\n")
        
        testbench.append("endmodule")
        return '\n'.join(testbench)
    
    def write_testbench(self):
        """Write the generated testbench to a Verilog file."""
        tb_code = self.generate_testbench()
        tb_filename = self.module_name + "_tb.v"
        with open(tb_filename, 'w') as tb_file:
            tb_file.write(tb_code)
        print(f"Testbench generated: {tb_filename}")

def main(verilog_file, module_name, clock_period):
    """Main function to execute the testbench generation for a specific module."""
    generator = TestBenchGenerator(verilog_file, module_name, clock_period)
    generator.parse_verilog_module()
    generator.write_testbench()

if __name__ == "__main__":
    print("Script started ...")
    if len(sys.argv) != 4:
        print("Usage: python generate_tb.py <verilog_file> <module_name> <clock>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])

