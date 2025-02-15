"""
gadget for secure multiplication

"""

class HPC3:
    def __init__(self, d):
        """
        Initialise HPC3 with security order d (number of shares = d + 1)
        """
        self.d = d # security order
    def generate_multiply_function(self, var_a, var_b, var_c):
        """
        input:  [a0, a1, ..., ad]
                [b0, b1, ..., bd]
        output: [c0, c1, ..., cd]

        """
        d = self.d
        param_a = ", ".join([f"int {var_a}{i}" for i in range(d + 1)])
        param_b = ", ".join([f"int {var_b}{i}" for i in range(d + 1)])
        param_c = ", ".join([f"int* {var_c}{i}" for i in range(d + 1)])
        param_rand = ", ".join([f"int r{i}{j}" for i in range(d) for j in range(i + 1, d + 1)])

        param_prand = ", ".join([f"int p{i}{j}" for i in range(d) for j in range(i + 1, d + 1)])
        param_str = f"{param_a}, {param_b}, {param_c}, {param_rand}, {param_prand}" # function parameter list 
        # random number 
        helper_func = f"""
void hpc3_same_shares(int a_share, int b_share, int * u_share) {{
    * u_share  = a_share & b_share;
}}

void hpc3_v(int a_share, int b_share, int * v_share, int rand){{
    *v_share = b_share ^ rand;
    *v_share = *v_share & a_share;
}}

void hpc3_w(int a_share, int rand, int prand, int * w_share){{
    *w_share = ~(a_share) & rand;
    *w_share = *w_share ^ prand;
}}

void hpc3_xor_vw(int v_share, int w_share, int * u_share){{
    *u_share = v_share ^ w_share;
}}


"""
        # void multiply_different(int a_share, int b_share, int & u_share, int rand, int prand){{
        #     int v_share, w_share;
        #     hpc3_v(a_share, b_share, &v_share, rand);
        #     hpc3_w(a_share, rand, prand, &w_share);
        #     *u_share = v_share ^ w_share;
        # }}
        function_signature = f"void HPC3({param_str})"
        # store the functions body
        body_lines = []

        # generating decalarations for u_ij
        body_lines.append(f"\tint {', '.join([f'u{i}{j}' for i in range(d + 1) for j in range(d+1)])};\n") 
        body_lines.append(f"\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n")
        body_lines.append(f"\tint {', '.join([f'w{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n\n")
        for i in range(d + 1):
            for j in range(d+1):
                if i == j:
                    body_lines.append(f"\thpc3_same_shares({var_a}{i}, {var_b}{i}, &u{i}{i});\n\n")
                if i != j:

                    p_param = f"p{min(i, j)}{max(i, j)}"
                    r_param = f"r{min(i, j)}{max(i, j)}"
        
                    body_lines.append(f"\thpc3_v({var_a}{i}, {var_b}{j}, &v{i}{j} , {r_param});\n")

                    body_lines.append(f"\thpc3_w({var_a}{i}, {r_param}, {p_param}, &w{i}{j});\n")

                    body_lines.append(f"\thpc3_xor_vw(v{i}{j}, w{i}{j}, &u{i}{j});\n\n")
        
        
        for i in range(d + 1):
            body_lines.append(f"\t*c{i} = 0;\n")
            for j in range(d + 1):
                body_lines.append(f"\t*c{i} = *c{i} ^ u{i}{j};\n ")
                                
        body_lines.append("}")
        return [helper_func] +[function_signature]+ ["{\n"] + body_lines

class HPC2:
    def __init__(self, d):
        """
        Initialise HPC2 with security order d (number of shares = d + 1)
        """
        self.d = d # security order
    def generate_multiply_function(self, var_a, var_b, var_c):
        """
        input:  [a0, a1, ..., ad]
                [b0, b1, ..., bd]
        output: [c0, c1, ..., cd]

        """
        d = self.d
        param_a = ", ".join([f"int {var_a}{i}" for i in range(d + 1)])
        param_b = ", ".join([f"int {var_b}{i}" for i in range(d + 1)])
        param_c = ", ".join([f"int * {var_c}{i}" for i in range(d + 1)])
        param_rand = ", ".join([f"int r{i}{j}" for i in range(d) for j in range(i + 1, d + 1)])

        # param_prand = ", ".join([f"p{i}" for i in range(d + 1)])
        param_str = f"{param_a}, {param_b}, {param_c}, {param_rand}" # function parameter list 
        # random number 
        helper_func = f"""
void hpc2_same_shares(int a_share, int b_share, int * u_share) {{
    * u_share  = a_share & b_share;
}}

void hpc2_v(int a_share, int b_share, int * v_share, int rand){{
    *v_share = b_share ^ rand;
    *v_share = *v_share & a_share;
}}

void hpc2_w(int a_share, int rand, int *  w_share){{
    *w_share = ~(a_share) & rand;
}}

void hpc2_xor_vw(int v_share, int w_share, int * u_share){{
    *u_share = v_share ^ w_share;
}}

"""
        # void multiply_different(int a_share, int b_share, int & u_share, int rand, int prand){{
        #     int v_share, w_share;
        #     hpc3_v(a_share, b_share, &v_share, rand);
        #     hpc3_w(a_share, rand, prand, &w_share);
        #     *u_share = v_share ^ w_share;
        # }}
        function_signature = f"void HPC2({param_str})"
        # store the functions body
        body_lines = []

        # generating decalarations for u_ij
        body_lines.append(f"\tint {', '.join([f'u{i}{j}' for i in range(d + 1) for j in range(d+1)])};\n") 
        body_lines.append(f"\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n\n")
        body_lines.append(f"\tint {', '.join([f'w{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n\n")
        for i in range(d + 1):
            for j in range(d+1):
                if i == j:
                    body_lines.append(f"\thpc2_same_shares({var_a}{i}, {var_b}{i}, &u{i}{i});\n")
                if i != j:
                    r_param = f"r{min(i, j)}{max(i, j)}"
                    body_lines.append(f"\thpc2_v({var_a}{i}, {var_b}{j}, &v{i}{j} , {r_param});\n")

                    body_lines.append(f"\thpc2_w({var_a}{i}, {r_param}, &w{i}{j});\n")

                    body_lines.append(f"\thpc2_xor_vw(v{i}{j}, w{i}{j}, &u{i}{j});\n\n")

        for i in range(d + 1):
            body_lines.append(f"\t\t*c{i} = 0;\n")
            for j in range(d + 1):
                body_lines.append(f"\t\t*c{i} = *c{i} ^ u{i}{j};\n ")

        body_lines.append("}")
        return [helper_func] +[function_signature]+ ["{\n"] + body_lines


class Domand:
    def __init__(self, d):
        """
            Initialise HPC2 with security order d (number of shares = d + 1
        """
        self.d = d
    
    def generate_multiply_function(self, var_a, var_b, var_c):

        print("-------------------------------------------------------")
        print("| Printing [Domand DEFINITION] for {d} order security...")
        print("-------------------------------------------------------")
        
        d = self.d
        
        param_a = ", ".join([f"int {var_a}{i}" for i in range(d + 1)])
        param_b = ", ".join([f"int {var_b}{i}" for i in range(d + 1)])
        param_c = ", ".join([f"int * {var_c}{i}" for i in range(d + 1)])
        param_rand = ", ".join([f"int r{i}" for i in range(d + 1)])
        param_str = f"{param_a}, {param_b}, {param_c}, {param_rand}" # function parameter list 
        
        function_signature = f"void domand({param_str})"

        body_lines = []
        # body_lines.append(f"\t\tint {', '.join([f'u{i}{j}' for i in range(d + 1) for j in range(d+1)])};\n") 
        # body_lines.append(f"\t\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n\n")

        # generating decalarations for u_ij
        body_lines.append(f"\t\tint {', '.join([f'u{i}{j}' for i in range(d + 1) for j in range(d+1)])};\n") 

        for i in range(d + 1):
            # body_lines.append("\t\t// same share terms\n")
            body_lines.append(f"\t\tu{i}{i} = {var_a}{i} & {var_b}{i};\n\n")
            # body_lines.append("\t\t// different share terms\n")
            for j in range(d + 1):
                if(i != j):
                    body_lines.append(f"\t\tu{i}{j} = {var_a}{i} & {var_b}{j};\n")
                    body_lines.append(f"\t\tu{i}{j} = u{i}{j} ^ r{j};\n")
            body_lines.append("\n")

        for i in range(d + 1):
            body_lines.append(f"\t\t*c{i} = 0;\n")
            for j in range(d + 1):
                body_lines.append(f"\t\t*c{i} = *c{i} ^ u{i}{j};\n ")
        
        body_lines.append("}")
            
        return [function_signature]+ ["{\n"] + body_lines

class HPC1:
    def __init__(self, d):
        """
        Initialise HPC3 with security order d (number of shares = d + 1)
        """
        self.d = d # security order
    def generate_multiply_function(self, var_a, var_b, var_c):
        """
        input:  [a0, a1, ..., ad]
                [b0, b1, ..., bd]
        output: [c0, c1, ..., cd]

        """
        d = self.d
        param_a = ", ".join([f"int {var_a}{i}" for i in range(d + 1)])
        param_b = ", ".join([f"int {var_b}{i}" for i in range(d + 1)])
        param_c = ", ".join([f"int* {var_c}{i}" for i in range(d + 1)])
        param_rand = ", ".join([f"int r{i}" for i in range(d + 1)])
        param_prand = ", ".join([f"int p{i}{j}" for i in range(d) for j in range(i + 1, d + 1)])

        param_str = f"{param_a}, {param_b}, {param_c}, {param_rand}, {param_prand}" # function parameter list 
        # # random number 
        helper_func = f"""

// {d} order secure hpc1 code 
// same domain term e.g. (bi = bi & ai)
void hpc1_same_shares(int a_share, int b_share, int rand, int * v_share) {{

    b_share = b_share ^ rand;
    * v_share  = a_share & b_share;
}}

// cross domain terms ( e.g., vij = ai & bj )
void hpc1_cross_domain(int a_share, int b_share, int * v_share, int rand, int prand){{

    //refresh sharing of b_share
    b_share = b_share ^ rand;

    int a_and_b = a_share & b_share;
    *v_share = b_share ^ prand;
}}

        """

        function_signature = f"void HPC1({param_str})"
        # print(f"printing function signature for hpc1:\n {function_signature}")
        # store the functions body
        body_lines = []

        # generating decalarations for u_ij
        body_lines.append(f"\t\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1)])};\n") 
        # body_lines.append(f"\t\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n")
        
        for i in range(d + 1):
            for j in range(d+1):
                if i == j:
                    body_lines.append(f"\t\thpc1_same_shares({var_a}{i}, {var_b}{i}, r{i}, &v{i}{i});\n")
                if i != j:
                    p_param = f"p{min(i, j)}{max(i, j)}"
                    body_lines.append(f"\t\thpc1_cross_domain({var_a}{i}, {var_b}{j}, &v{i}{j} , r{j}, {p_param});\n")

        
        
        for i in range(d + 1):
            body_lines.append(f"\t\t*c{i} = 0;\n")
            for j in range(d + 1):
                body_lines.append(f"\t\t*c{i} = *c{i} ^ v{i}{j};\n ")
                                
        body_lines.append("}")
        return [helper_func] +["\n"]+[function_signature]+ ["{\n"] + body_lines

class Comar:
    def __init__(self, d):
        """
        Initialise HPC3 with security order d (number of shares = d + 1)
        """
        self.d = d # security order
    def generate_multiply_function(self, var_a, var_b, var_c):
        """
        input:  [a0, a1, ..., ad]
                [b0, b1, ..., bd]
        output: [c0, c1, ..., cd]

        """
        d = self.d
        param_a = ", ".join([f"int {var_a}{i}" for i in range(d + 1)])
        param_b = ", ".join([f"int {var_b}{i}" for i in range(d + 1)])
        param_c = ", ".join([f"int* {var_c}{i}" for i in range(d + 1)])
        param_rand = ", ".join([f"int r{i}" for i in range(d + 1)])
        param_prand = ", ".join([f"int p{i}{j}" for i in range(d) for j in range(i + 1, d + 1)])

        param_str = f"{param_a}, {param_b}, {param_c}, {param_rand}, {param_prand}" # function parameter list 
        # # random number 
        helper_func = f"""

// {d} order secure hpc1 code 
// same domain term e.g. (bi = bi & ai)
void hpc1_same_shares(int a_share, int b_share, int rand, int * v_share) {{

    b_share = b_share ^ rand;
    * v_share  = a_share & b_share;
}}

// cross domain terms ( e.g., vij = ai & bj )
void hpc1_cross_domain(int a_share, int b_share, int * v_share, int rand, int prand){{

    //refresh sharing of b_share
    b_share = b_share ^ rand;

    int a_and_b = a_share & b_share;
    *v_share = b_share ^ prand;
}}

        """

        function_signature = f"void HPC1({param_str})"
        # print(f"printing function signature for hpc1:\n {function_signature}")
        # store the functions body
        body_lines = []

        # generating decalarations for u_ij
        body_lines.append(f"\t\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1)])};\n") 
        # body_lines.append(f"\t\tint {', '.join([f'v{i}{j}' for i in range(d + 1) for j in range(d+1) if i != j])};\n")
        
        for i in range(d + 1):
            for j in range(d+1):
                if i == j:
                    body_lines.append(f"\t\thpc1_same_shares({var_a}{i}, {var_b}{i}, r{i}, &v{i}{i});\n")
                if i != j:
                    p_param = f"p{min(i, j)}{max(i, j)}"
                    body_lines.append(f"\t\thpc1_cross_domain({var_a}{i}, {var_b}{j}, &v{i}{j} , r{j}, {p_param});\n")

        
        
        for i in range(d + 1):
            body_lines.append(f"\t\t*c{i} = 0;\n")
            for j in range(d + 1):
                body_lines.append(f"\t\t*c{i} = *c{i} ^ v{i}{j};\n ")
                                
        body_lines.append("}")
        return [helper_func] +["\n"]+[function_signature]+ ["{\n"] + body_lines


import os
def generate_and_write_function(class_name, d, a, b, c, filename_prefix, output_folder="gadget_output"):
    """
    Generates a multiply function using the given class, writes it to a C file, and prints the output.
    class_name: The class to instantiate (Domand, HPC1, HPC2, etc.)
    d: Security order parameter
    a: First input variable name
    b: Second input variable name
    c: Output variable name
    filename_prefix: Prefix for the output C file
    output_folder: floder to store generated test files
    """

    os.makedirs(output_folder, exist_ok=True)
    instance = class_name(d)
    function_def = instance.generate_multiply_function(a, b, c)
    c_filename = os.path.join(output_folder, f"{filename_prefix}_generated.c")
    
    with open(c_filename, "w") as f:
        f.write(f"/* {filename_prefix.upper()} Function Definition */\n")
        f.write("".join(function_def))
    
    print("-" * 56)
    print(f"| Printing [{filename_prefix.upper()} DEFINITION] for {d} order security... ")
    print("-" * 56)
    print("".join(function_def))
    print("-" * 56)
    print(f"C file '{c_filename}' created successfully.\n")

# Define common parameters
a, b, c = "a", "b", "c"

# Run function for different classes
generate_and_write_function(Domand, 2, a, b, c, "domand")
generate_and_write_function(HPC1, 1, a, b, c, "hpc1")
generate_and_write_function(HPC2, 2, a, b, c, "hpc2")
generate_and_write_function(HPC3, 2, a, b, c, "hpc3")
