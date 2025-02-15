from pycparser import parse_file, c_ast
from pycparser.c_generator import CGenerator
import re
import copy



# to do :
# write the generic gadget class
# HPC1
# HPC2
# HPC3
# comar
# domand
# write automatic test bench generation code.
#

def preprocess_file(input_file, output_file):
    try:
        with open(input_file, "r") as infile, open(output_file, "w") as outfile:
            code = infile.read()
            
            # Remove single-line comments
            code = re.sub(r"//.*", "", code)
            
            # Remove multi-line comments
            code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
            
            # Remove preprocessor directives like #include
            lines = code.splitlines()
            clean_lines = [line for line in lines if not line.strip().startswith("#")]
            
            # Write the cleaned lines to the output file
            outfile.write("\n".join(clean_lines))
            
        print(f"Preprocessed file created: {output_file}")
    except Exception as e:
        print(f"Error during preprocessing: {e}")



class FunctionProcessor(c_ast.NodeVisitor):
    def __init__(self, num_shares = 2):
        self.local_vars = {}
        self.current_function = None
        self.block_stack = []
        self.tac_generator = TACGenerator()
        self.gadget_count = 0 # counter for  compution 
        self.num_shares = num_shares
        self.function_signatures = {}
        # self.random_varible_used = 0 # to count number of random varible used
        self.random_counters = {}  

    def handle_function_call_in_assignment(self, lhs, func_name, args, new_params):
        """
        Converts a function call inside an assignment to a call with output pointers and randomness.
        - lhs: Assignment target (e.g., 'e' in 'e = G4_mul(a, b)')
        - func_name: Name of the called function.
        - args: List of function arguments.
        """
        
        # print(f"argument of function {func_name} {args}")
        if func_name in self.function_signatures:
            func_info = self.function_signatures[func_name]
            num_random_vars = func_info["num_random_vars"]
            num_output_vars = func_info["num_output_vars"]

            new_args = []
            
            # Convert input arguments to shares
            for arg in args:
                for i in range(self.num_shares):
                    new_args.append(c_ast.ID(name=f"{arg}_{i}"))

            # Use assignment target as output pointers
            for i in range(self.num_shares):
                new_args.append(
                    c_ast.UnaryOp(op="&", expr=c_ast.ID(name=f"{lhs.strip()}_{i}"))
                )
            random_counter = self.random_counters[self.current_function]
            # Add randomness parameters
            for i in range(num_random_vars):
                random_var_name = f"r{random_counter}"
                random_counter+=1
                new_params.append(
                    c_ast.Decl(
                        name = random_var_name,
                        quals = [],
                        storage = [],
                        funcspec = [],
                        align=None,
                        type=c_ast.TypeDecl(
                            declname=random_var_name,
                            align=None,
                            quals=[],
                            type=c_ast.IdentifierType(names=["int"])
                        ),
                    init=None,
                    bitsize=None
                    )
                )
                new_args.append(c_ast.ID(name=random_var_name))
            self.random_counters[self.current_function] = random_counter
            # Create modified function call
            new_func_call=  c_ast.FuncCall(
                name=c_ast.ID(name=func_name),
                args=c_ast.ExprList(exprs=new_args)
            )
        
        return new_func_call, num_random_vars

    def create_share_expression(self, expr, share_index):
        if isinstance(expr, c_ast.BinaryOp):
            # Handle binary operations (e.g., a + b)
            return c_ast.BinaryOp(
                op=expr.op,
                left=self.create_share_expression(expr.left, share_index),
                right=self.create_share_expression(expr.right, share_index)
            )
        elif isinstance(expr, c_ast.UnaryOp):
            # Handle unary operations (e.g., -a)
            return c_ast.UnaryOp(
                op=expr.op,
                expr=self.create_share_expression(expr.expr, share_index)
            )
        elif isinstance(expr, c_ast.ID):
            # Handle variable references (e.g., a)
            return c_ast.ID(name=f"{expr.name}_{share_index}")
        elif isinstance(expr, c_ast.Constant):
            # Handle constants (e.g., 5)
            return expr  # Constants are the same for all shares
        else:
            raise NotImplementedError(f"Unsupported expression type: {type(expr)}")
    
    def create_share_function_call(self, func_call, share_index):
        # Handle function calls (e.g., foo())
        return c_ast.FuncCall(
            name=func_call.name,
            args=c_ast.ExprList(
                exprs=[self.create_share_expression(arg, share_index) for arg in func_call.args.exprs]
            )
        )

    def expression_to_string(self, expr):
        if isinstance(expr, c_ast.Constant):
            return expr.value
        elif isinstance(expr, c_ast.ID):
            return expr.name
        elif isinstance(expr, c_ast.BinaryOp):
            return f"{self.expression_to_string(expr.left)} {expr.op} {self.expression_to_string(expr.right)}"
        elif isinstance(expr, c_ast.UnaryOp):
            return f"{expr.op}{self.expression_to_string(expr.expr)}"
        elif isinstance(expr, c_ast.FuncCall):
            return f"{expr.name.name}({', '.join(self.expression_to_string(arg) for arg in expr.args.exprs)})"
        elif isinstance(expr, c_ast.InitList):
            return "{" + ", ".join(self.expression_to_string(e) for e in expr.exprs) + "}" 
        else:
            raise NotImplementedError(f"Unsupported expression type: {type(expr)}")
    
    def evaluate_expression(self, expr):
        """ Safely extract or evaluate an integer expression from AST """
        if isinstance(expr, c_ast.Constant):
            return int(expr.value)
        elif isinstance(expr, c_ast.UnaryOp) and expr.op == '-':
            return -self.evaluate_expression(expr.expr)
        elif isinstance(expr, c_ast.BinaryOp):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            return eval(f"{left} {expr.op} {right}")
        else:
            raise NotImplementedError("Loop bounds must be integer constants or simple expressions.")


    import copy  # <-- Import copy module

    def visit_For(self, node):
        """ Unrolls the for loop dynamically """
        if not isinstance(node.init, c_ast.Assignment) or not isinstance(node.cond, c_ast.BinaryOp):
            raise NotImplementedError("Only simple 'for' loops with integer conditions are supported.")

        loop_var = node.init.lvalue.name  # Loop variable like `i`
        start_value = self.evaluate_expression(node.init.rvalue)  # Initialization value
        end_value = self.evaluate_expression(node.cond.right)  # Termination value

        # Determine step size dynamically
        if isinstance(node.next, c_ast.UnaryOp):
            if node.next.op in ["p--", "--"]:
                step = -1
            elif node.next.op in ["p++", "++"]:
                step = 1
            else:
                raise NotImplementedError(f"Unsupported unary operation: {node.next.op}")
        elif isinstance(node.next, c_ast.Assignment):
            step = self.evaluate_expression(node.next.rvalue)  # Handle i = i + step
        else:
            raise NotImplementedError("Unsupported step expression in for loop.")

        unrolled_statements = []
        current_value = start_value

        while current_value >= end_value if step < 0 else current_value <= end_value:
            print(f"-------------------------------------------\n[current value] : {current_value}")
            
            # Deep copy of loop body before modification
            loop_body_copy = copy.deepcopy(node.stmt)

            if isinstance(loop_body_copy, c_ast.Compound):
                for sub_stmt in loop_body_copy.block_items:
                    unrolled_statements.append(self.replace_loop_var(sub_stmt, loop_var, current_value))
            else:
                unrolled_statements.append(self.replace_loop_var(loop_body_copy, loop_var, current_value))

            current_value += step

        node.stmt = c_ast.Compound(block_items=unrolled_statements)  # Modify the AST directly
        return node



    def replace_loop_var(self, stmt, loop_var, value):
        """ Replace loop variable occurrences with a constant value, handling compound assignments. """
        class ReplaceLoopVar(c_ast.NodeVisitor):
            def __init__(self, var_name, replace_value):
                self.var_name = var_name
                self.replace_value = replace_value
                # self.modified_node = None  # Store modified node

            def visit(self, node):
                """ Recursively visit nodes and replace loop variables """
                if isinstance(node, c_ast.ID) and node.name == self.var_name:
                    print(f"[inside replace loop var]\nloop variable : {self.var_name} \nloop variable value : {self.replace_value}")
                    return c_ast.Constant(type="int", value=str(self.replace_value))
                

                elif isinstance(node, c_ast.Assignment):
                    node.lvalue = self.visit(node.lvalue)
                    node.rvalue = self.visit(node.rvalue)

                    # Handle compound assignment operators (>>=, +=, -=, etc.)
                    if node.op in {">>=", "<<=", "+=", "-=", "*=", "/=", "&=", "|=", "^="}:
                        expanded_rhs = c_ast.BinaryOp(
                            op=node.op[:-1],  # Convert `>>=` to `>>`, `+=` to `+`, etc.
                            left=node.lvalue,
                            right=node.rvalue
                        )
                        node.op = "="  # Convert `>>=` to `=`
                        node.rvalue = expanded_rhs  # Assign the new expanded expression

                    return node

                elif isinstance(node, c_ast.BinaryOp):
                    node.left = self.visit(node.left)
                    node.right = self.visit(node.right)
                    return node

                elif isinstance(node, c_ast.Compound):
                    node.block_items = [self.visit(sub_stmt) for sub_stmt in node.block_items if sub_stmt]
                    return node

                return node  # Return unchanged node if no modifications
        replacer = ReplaceLoopVar(loop_var, value)
        # print()
        transformed_stmt = replacer.visit(stmt)

        return transformed_stmt if transformed_stmt is not None else stmt


    
    def visit_FuncDef(self, node):
        self.current_function = node.decl.name
        num_shares = self.num_shares

        # Store function metadata
        function_metadata = {
            "decl": node.decl,
            "num_random_vars": 0,
            "num_output_vars": num_shares
        }

        self.random_counters[self.current_function] = 0

        # Store local variable list
        self.local_vars[self.current_function] = {
            "parameters": [],
            "local_vars": []
        }

        # Parse existing parameters and split them into shares
        params = node.decl.type.args.params
        new_params = []

        if params:
            for param in params:
                if isinstance(param.type, c_ast.TypeDecl):
                    param_name = param.name
                    param_type = " ".join(param.type.type.names)

                    # Remove the original parameter and replace it with shares
                    for i in range(num_shares):
                        share_param_name = f"{param_name}_{i}"
                        new_params.append(
                            c_ast.Decl(
                                name=share_param_name,
                                quals=[],
                                storage=[],
                                funcspec=[],
                                align=None,
                                type=c_ast.TypeDecl(
                                    declname=share_param_name,
                                    align=None,
                                    quals=[],
                                    type=c_ast.IdentifierType(names=[param_type])
                                ),
                                init=None,
                                bitsize=None
                            )
                        )
                        self.local_vars[self.current_function]["parameters"].append((share_param_name, param_type))
                elif isinstance(param.type, c_ast.ArrayDecl):
                    param_name = param.name
                    base_type = "".join(param.type.type.type.names) # extract the type
                    # keep array as is
                    new_params.append(
                        c_ast.Decl(
                            name = param_name,
                            quals=[],
                            storage=[],
                            funcspec=[],
                            align=None,
                            type=c_ast.ArrayDecl(
                                type=c_ast.TypeDecl(
                                    declname=param_name,
                                    align=None,
                                    quals=[],
                                    type=c_ast.IdentifierType(names=[base_type])
                                ),
                                dim=param.type.dim,
                                dim_quals=[]
                            ),
                            init=None,
                            bitsize=None
                        )
                    )
                    self.local_vars[self.current_function]["parameters"].append((param_name,f"{base_type}"))
        # Modify the return type to `void` and add output pointers for each share
        return_type = node.decl.type.type.type.names
        if return_type != ["void"]:  # Only modify if it's not already `void`
            output_var_name = f"{node.decl.name}_output"
            output_var_type = " ".join(return_type)

            # Change the function's return type to `void`
            node.decl.type.type.type.names = ["void"]

            # Add output pointers for each share to the parameter list
            for i in range(num_shares):
                new_params.append(
                    c_ast.Decl(
                        name=f"{output_var_name}_{i}",
                        quals=[],
                        storage=[],
                        funcspec=[],
                        align=None,
                        type=c_ast.PtrDecl(
                            quals=[],
                            type=c_ast.TypeDecl(
                                declname=f"{output_var_name}_{i}",
                                align=None,
                                quals=[],
                                type=c_ast.IdentifierType(names=[output_var_type])
                            )
                        ),
                        init=None,
                        bitsize=None
                    )
                )

                # replace return stmt with pointer
                self.replace_return_with_pointer(node.body, output_var_name)
        lhs = None
        # Process local variables declarations and split them into shares
        local_declarations = []
        # loop_body = []
        if node.body.block_items:
            for item in node.body.block_items:
                if isinstance(item, c_ast.Decl):
                    var_name = item.name
                    if isinstance(item.type, c_ast.ArrayDecl):
                        # handling array declaration
                        element_type = "".join(item.type.type.type.names)
                        var_init = item.init
                        if isinstance(item.type.dim, c_ast.Constant):
                            array_size = int(item.type.dim.value) # fixed size array
                        elif isinstance(item.type.dim, c_ast.ID):
                            array_size = item.type.dim.name # varibake length array int a[n];
                        else:
                            array_size = None 
                        if array_size is None and isinstance(item.init, c_ast.InitList):
                            self.local_vars[self.current_function]["local_vars"].append((f"{var_name}[]", element_type,var_init))
                        else:
                            self.local_vars[self.current_function]["local_vars"].append((f"{var_name}[{array_size}]", element_type, var_init))
                        
                    else:
                        var_type = "".join(item.type.type.names)
                        var_init = item.init  # Capture initialization if it exists
                    # Split the variable into shares
                        for i in range(num_shares):
                            share_var_name = f"{var_name}_{i}"
                            share_init = None

                            if var_init:
                                lhs = var_name
                                if isinstance(var_init, c_ast.Constant):
                                    # Handle constants (int, bool, double, etc.)
                                    share_init = c_ast.Constant(
                                        type=var_init.type,
                                        value=var_init.value
                                    )
                                elif isinstance(var_init, c_ast.ID):
                                    # Handle references to other variables (e.g., int a = b;)
                                    share_init = c_ast.ID(name=f"{var_init.name}_{i}")
                                elif isinstance(var_init, c_ast.BinaryOp):
                                    # Handle binary expressions (e.g., int a = 5 + 3;)
                                    share_init = self.create_share_expression(var_init, i)
                                elif isinstance(var_init, c_ast.UnaryOp):
                                    # Handle unary expressions (e.g., int a = -b;)
                                    share_init = self.create_share_expression(var_init, i)
                                elif isinstance(var_init, c_ast.FuncCall):
                                    # Handle function calls (e.g., int a = foo();)
                                    share_init = self.create_share_function_call(var_init, i)
                                else:
                                    # Handle other cases (e.g., arrays, structs, etc.)
                                    raise NotImplementedError(f"Unsupported initialization type: {type(var_init)}")

                        
                            self.local_vars[self.current_function]["local_vars"].append((share_var_name, var_type, share_init))
                elif isinstance(item, c_ast.For):
                    print(f"processing for loop")
                    self.visit_For(item)
                

        # Generate TAC and get temporary variables
        tac, temp_vars = self.tac_generator.generate(node.body)

        # Add temporary variables as shares
        for temp_var, temp_type in temp_vars:
            for i in range(num_shares):
                self.local_vars[self.current_function]["local_vars"].append((f"{temp_var}_{i}", temp_type, None))

        # Group all local variables by type for declaration
        grouped_vars = {}
        for var_name, var_type, var_init in self.local_vars[self.current_function]["local_vars"]:
            if var_type not in grouped_vars:
                grouped_vars[var_type] = []
            if var_init:
                var_name += f" = {self.expression_to_string(var_init)}"
            grouped_vars[var_type].append(var_name)

        # Emit grouped local variable declarations
        for var_type, var_names in grouped_vars.items():
            local_declarations.append(
                c_ast.Decl(
                    name=None,
                    quals=[],
                    storage=[],
                    funcspec=[],
                    align=None,
                    type=c_ast.TypeDecl(
                        declname=", ".join(var_names),
                        align=None,
                        quals=[],
                        type=c_ast.IdentifierType(names=[var_type])
                    ),
                    init=None,
                    bitsize=None
                )
            )

        # Replace the function body with TAC instructions and prepend declarations
        tac_statements = []
        random_counter = self.random_counters[self.current_function]

        for instr in tac:
            if ' = ' in instr:  # Handle assignments
                lhs, rhs = instr.split(' = ', 1)

                if '(' in rhs:
                    func_name = rhs.split('(', 1)[0].strip()
                    args_str = rhs[rhs.find("(")+1 : rhs.rfind(")")].strip()
                    args = [arg.strip() for arg in args_str.split(',')]

                    # Convert TAC function call to AST with shares
                    new_func_call, random_used = self.handle_function_call_in_assignment(lhs, func_name, args, new_params)
                    if new_func_call:
                        tac_statements.append(new_func_call)
                        continue
                elif '&' in rhs:
                    operands = rhs.split('&')
                    left = operands[0].strip()
                    right = operands[1].strip()

                    # Check if the operation is & and both operands are variables
                    if left.isidentifier() and right.isidentifier():
                        self.gadget_count += 1
                        random_var = f"r{random_counter}"
                        random_counter += 1
                        function_metadata["num_random_vars"] += 1

                        # Declare random variable
                        # depends on the type of gadget used

                        
                        new_params.append(
                            c_ast.Decl(
                                name=random_var,
                                quals=[],
                                storage=[],
                                funcspec=[],
                                align=None,
                                type=c_ast.TypeDecl(
                                    declname=random_var,
                                    align=None,
                                    quals=[],
                                    type=c_ast.IdentifierType(names=["int"])
                                ),
                                init=None,
                                bitsize=None
                            )
                        )
                        # Replace & operation with the function call
                        tac_statements.append(
                            c_ast.FuncCall(
                                name=c_ast.ID(name="domand"),
                                args=c_ast.ExprList(
                                    exprs=[
                                        c_ast.ID(name=f"&{lhs.strip()}_{i}") for i in range(num_shares)
                                    ] + [
                                        c_ast.ID(name=f"{left}_{i}") for i in range(num_shares)
                                    ] + [
                                        c_ast.ID(name=f"{right}_{i}") for i in range(num_shares)
                                    ] + [
                                        c_ast.ID(name=random_var)  # Randomness
                                    ]
                                )
                            )
                        )
                        self.random_counters[self.current_function] = random_counter
                        continue  # Skip the default processing for & operation

                # Handle shares for assignments
                rhs_parts = rhs.split()
                for i in range(num_shares):
                    rhs_shares = " ".join([f"{part}_{i}" if part.isidentifier() else part for part in rhs_parts])
                    tac_statements.append(
                        c_ast.Assignment(
                            op='=',
                            lvalue=c_ast.ID(name=f"{lhs.strip()}_{i}"),
                            rvalue=c_ast.ID(name=rhs_shares)
                        )
                    )
            elif '(' in instr and ')' in instr and not '=' in instr:  # Handle function calls
                func_name = instr.split('(', 1)[0].strip()
                args_str = instr.split('(', 1)[1].rstrip(')').strip()
                args = [arg.strip() for arg in args_str.split(',')]

                # Dynamically handle any function call for shares
                for i in range(num_shares):
                    # Generate the function call with shares
                    share_args = [
                        c_ast.ID(name=f"&{args[0]}_{i}"),  # Output share 0
                        c_ast.ID(name=f"&{args[1]}_{i}"),  # Output share 1
                    ] + [
                        c_ast.ID(name=f"{arg}_{i}") for arg in args[2:]  # Input shares
                    ] + [
                        c_ast.ID(name=random_var)  # Randomness
                    ]
                    tac_statements.append(
                        c_ast.FuncCall(
                            name=c_ast.ID(name=func_name),
                            args=c_ast.ExprList(exprs=share_args)
                        )
                    )
            else:
                print(f"Skipping invalid TAC: {instr}")

        # # Ensure the final result is assigned to the output pointers
        # for i in range(num_shares):
        #     tac_statements.append(
        #         c_ast.Assignment(
        #             op='=',
        #             lvalue=c_ast.UnaryOp(op='*', expr=c_ast.ID(name=f"{output_var_name}_{i}")),
        #             rvalue=c_ast.ID(name=f"{lhs.strip()}_{i}")
        #         )
        #     )

        # Update the parameters in the function definition
        node.decl.type.args.params = new_params
        function_metadata["num_random_vars"] = self.random_counters[self.current_function]
        self.function_signatures[self.current_function] = function_metadata

        # Combine local declarations and TAC statements
        node.body.block_items = local_declarations + tac_statements

        # Emit the modified function to the terminal
        self.emit_function(node)


    def replace_return_with_pointer(self, body, output_var_name):
        if not body or not body.block_items:
            return

        for i, stmt in enumerate(body.block_items):
            if isinstance(stmt, c_ast.Return):
                # Replace `return expr;` with `*output_var_name = expr;`
                body.block_items[i] = c_ast.Assignment(
                    op='=',
                    lvalue=c_ast.UnaryOp(
                        op='*',
                        expr=c_ast.ID(name=output_var_name)
                    ),
                    rvalue=stmt.expr
                )
            elif isinstance(stmt, c_ast.Compound):
                # Recursively handle nested blocks
                self.replace_return_with_pointer(stmt, output_var_name)

    
    def emit_function(self, node):
        # Emit the modified function definition
        # print(f"Modified Function: {node.decl.name}")
        print(self.to_c_code(node))

    def emit_tac(self, tac):
        # Emit the TAC
        print(f"TAC for {self.current_function}:")
        for instruction in tac:
            print(instruction)

    def to_c_code(self, node):
        # Utility to convert an AST node back to C code
        from pycparser.c_generator import CGenerator
        generator = CGenerator()
        return generator.visit(node)
    
    def save_to_file(self, node, original_file):
        # from pycparser.c_generator import CGenerator
        # print("modified AST before")
        # node.show()
        generator = CGenerator()

        # Generate the modified C code
        modified_code = generator.visit(node)
        full_code = """"""
        if self.gadget_count > 0:
            full_code = """
void domand(int a0, int a1, int b0, int b1, int *y0, int *y1, int z)
{
    int z0;
    z0 = z % 2;
    int i1, i2, p2, p3, p1, p4;
    p2 = a0 & b1;
    i1 = p2 ^ z0;
    p3 = a1 & b0;
    i2 = p3 ^ z0;
    p1 = a0 & b0;
    p4 = a1 & b1;
    *y0 = reg(i1) ^ p1;
    *y1 = reg(i2) ^ p4;
}

"""  + modified_code
        # Create a new file name with the prefix "modified_"
        new_file_name = f"modified_{original_file}"
        with open(new_file_name, "w") as f:
            f.write(full_code)

        print(f"Modified file saved as: {new_file_name}")


    

class TACGenerator(c_ast.NodeVisitor):
    def __init__(self):
        self.temp_count = 0
        self.tac = []
        self.temp_vars = []  # Track temporary variables and their types
        self.gadget_count = 0

    def new_temp(self, var_type="int"):
        """Generate a new temporary variable with a specified type."""
        temp_var = f"t{self.temp_count}"
        self.temp_count += 1
        self.temp_vars.append((temp_var, var_type))  # Track the new temporary variable and its type
        return temp_var

    # def visit_For(self, node):
    #     """unroll the loop"""
    #     # process loop initialisation
    #     self.visit(node.init)
    #     # determine the number of iteration
    #     num_iteration = 8

    #     for i in range(num_iteration):
    #         if node.cond:
    #             self.visit(node.cond)

    #         self.visit(node.body)

    #         if node.next:
    #             self.visit(node.next)


    # def visit_For(self, node):
    #     """ Unroll loops dynamically while generating TAC """
    #     if not isinstance(node.init, c_ast.Assignment) or not isinstance(node.cond, c_ast.BinaryOp):
    #         raise NotImplementedError("Only simple 'for' loops with integer conditions are supported.")

    #     loop_var = node.init.lvalue.name
    #     start_value = self.evaluate_expression(node.init.rvalue)
    #     end_value = self.evaluate_expression(node.cond.right)

    #     # Determine step size dynamically
    #     if isinstance(node.next, c_ast.UnaryOp):
    #         if node.next.op in ["p--", "--"]:
    #             step = -1
    #         elif node.next.op in ["p++", "++"]:
    #             step = 1
    #         else:
    #             raise NotImplementedError(f"Unsupported unary operation: {node.next.op}")
    #     elif isinstance(node.next, c_ast.Assignment):
    #         step = self.evaluate_expression(node.next.rvalue)
    #     else:
    #         raise NotImplementedError("Unsupported step expression in for loop.")

    #     current_value = start_value

    #     while (current_value >= end_value if step < 0 else current_value <= end_value):
    #         print(f"Generating TAC for loop iteration with {loop_var} = {current_value}")

    #         if isinstance(node.stmt, c_ast.Compound):
    #             for sub_stmt in node.stmt.block_items:
    #                 # Directly generate TAC instructions for each iteration
    #                 self.tac.append(self.replace_loop_var(sub_stmt, loop_var, current_value))
    #         else:
    #             self.tac.append(self.replace_loop_var(node.stmt, loop_var, current_value))

    #         current_value += step

    # def evaluate_expression(self, expr):
    #     """ Safely extract or evaluate an integer expression from AST """
    #     if isinstance(expr, c_ast.Constant):
    #         return int(expr.value)
    #     elif isinstance(expr, c_ast.UnaryOp) and expr.op == '-':
    #         return -self.evaluate_expression(expr.expr)
    #     elif isinstance(expr, c_ast.BinaryOp):
    #         left = self.evaluate_expression(expr.left)
    #         right = self.evaluate_expression(expr.right)
    #         return eval(f"{left} {expr.op} {right}")
    #     elif isinstance(expr, c_ast.ID):
    #         raise NotImplementedError(f"Variable '{expr.name}' used as loop bound; cannot resolve statically.")
    #     else:
    #         raise NotImplementedError("Loop bounds must be integer constants or simple expressions.")

    # def replace_loop_var(self, stmt, loop_var, value):
    #     """ Replace loop variable occurrences with a constant value, handling compound assignments. """
    #     class ReplaceLoopVar(c_ast.NodeVisitor):
    #         def __init__(self, var_name, replace_value):
    #             self.var_name = var_name
    #             self.replace_value = replace_value
    #             # self.modified_node = None  # Store modified node

    #         def visit(self, node):
    #             """ Recursively visit nodes and replace loop variables """
    #             if isinstance(node, c_ast.ID) and node.name == self.var_name:
    #                 print(f"[inside replace loop var]\nloop variable : {self.var_name} \nloop variable value : {self.replace_value}")
    #                 return c_ast.Constant(type="int", value=str(self.replace_value))
                

    #             elif isinstance(node, c_ast.Assignment):
    #                 node.lvalue = self.visit(node.lvalue)
    #                 node.rvalue = self.visit(node.rvalue)

    #                 # Handle compound assignment operators (>>=, +=, -=, etc.)
    #                 if node.op in {">>=", "<<=", "+=", "-=", "*=", "/=", "&=", "|=", "^="}:
    #                     expanded_rhs = c_ast.BinaryOp(
    #                         op=node.op[:-1],  # Convert `>>=` to `>>`, `+=` to `+`, etc.
    #                         left=node.lvalue,
    #                         right=node.rvalue
    #                     )
    #                     node.op = "="  # Convert `>>=` to `=`
    #                     node.rvalue = expanded_rhs  # Assign the new expanded expression

    #                 return node

    #             elif isinstance(node, c_ast.BinaryOp):
    #                 node.left = self.visit(node.left)
    #                 node.right = self.visit(node.right)
    #                 return node

    #             elif isinstance(node, c_ast.Compound):
    #                 node.block_items = [self.visit(sub_stmt) for sub_stmt in node.block_items if sub_stmt]
    #                 return node

    #             return node  # Return unchanged node if no modifications
    #     replacer = ReplaceLoopVar(loop_var, value)
    #     # print()
    #     return replacer.visit(stmt)


    def visit_Assignment(self, node):
        """Generate TAC for assignment statements."""
        if isinstance(node.lvalue, c_ast.ID):
            lvalue = node.lvalue.name
        elif isinstance(node.lvalue, c_ast.UnaryOp) and node.lvalue.op == '*':
            lvalue = f"*{self.visit(node.lvalue.expr)}"
        else:
            raise NotImplementedError(f"Unhandled lvalue type: {type(node.lvalue)}")

        # Visit the rvalue and pass the target variable
        if isinstance(node.rvalue, c_ast.BinaryOp):
            # Infer the type of the binary operation result
            var_type = self.infer_type(node.rvalue)
            self.visit_BinaryOp(node.rvalue, target_var=lvalue, var_type=var_type)
        elif isinstance(node.rvalue, c_ast.FuncCall):
            # Function call transformation
            func_name = node.rvalue.name.name
            args = [self.visit(arg) for arg in node.rvalue.args.exprs]

            # Infer the type of the function call result
            var_type = self.infer_type(node.rvalue)
            self.tac.append(f"{lvalue} = {func_name}({', '.join(args)});")
        else:
            rhs = self.visit(node.rvalue)
            self.tac.append(f"{lvalue} = {rhs}")

    def visit_BinaryOp(self, node, target_var=None, var_type="int"):
        """Optimized TAC for binary operations with function calls, avoiding duplicate function calls."""
        # If target_var is provided, use it for the final result
        result_var = target_var if target_var else self.new_temp(var_type)

        # Process left operand
        if isinstance(node.left, c_ast.FuncCall):
            left = self.visit_FuncCall(node.left, target_var=result_var)  # Reuse target_var
        else:
            left = self.visit(node.left)

        # Process right operand
        if isinstance(node.right, c_ast.FuncCall):
            right = self.visit_FuncCall(node.right)  # Create a temp only if needed
        else:
            right = self.visit(node.right)

        # Generate TAC for the binary operation
        self.tac.append(f"{result_var} = {left} {node.op} {right}")

        return result_var

    def visit_FuncCall(self, node, target_var=None):
        """Optimized function call handling: reuse target_var when possible."""
        func_name = node.name.name
        args = [self.visit(arg) for arg in node.args.exprs]

        # If function is inside a binary operation, reuse target_var
        result_var = target_var if target_var else self.new_temp()

        # Store function call in TAC
        self.tac.append(f"{result_var} = {func_name}({', '.join(args)})")

        return result_var

    def visit_Constant(self, node):
        """Handle constants."""
        return node.value

    def visit_ID(self, node):
        """Handle identifiers."""
        return node.name

    def infer_type(self, node):
        """Infer the type of an expression."""
        if isinstance(node, c_ast.Constant):
            # Infer type from constant value
            if node.type == "int":
                return "int"
            elif node.type == "float":
                return "float"
            elif node.type == "char":
                return "char"
            else:
                return "int"  # Default type
        elif isinstance(node, c_ast.ID):
            # Infer type from the variable's declaration (requires a symbol table)
            # For now, assume all variables are of type "int"
            return "int"
        elif isinstance(node, c_ast.BinaryOp):
            # Infer type from the operands
            left_type = self.infer_type(node.left)
            right_type = self.infer_type(node.right)
            # If both operands are of the same type, return that type
            if left_type == right_type:
                return left_type
            else:
                # If types differ, return the more general type (e.g., float > int)
                if "float" in [left_type, right_type]:
                    return "float"
                else:
                    return "int"
        elif isinstance(node, c_ast.FuncCall):
            # Infer type from the function's return type (requires a symbol table)
            # For now, assume all functions return "int"
            return "int"
        else:
            # Default type
            return "int"

    def generate(self, body):
        """Generate TAC for the given body."""
        self.tac = []  # Reset TAC
        self.temp_vars = []  # Reset temporary variables
        self.visit(body)
        return self.tac, self.temp_vars


import argparse


if __name__ == "__main__":
    input_file = "test.c"  # Input C file
    output_file = "test_no_includes.c"  # Output file without #include directives
    

    # # get user input 
    parser = argparse.ArgumentParser(description="| Preprocess C source code into a format suitable for input to maskedHLS tool |")
    # parser.add_argument("input_file", type=str, help="Path to the input C file.")
    # parser.add_argument("output_file",type = str, help = "Path to the output transformed C file.")
    parser.add_argument("--num_shares", type= int, default=2, help = "Number of shares to split variables into (default : 2)")

    args = parser.parse_args()
    # input_file = args.input_file
    # output_file = args.output_file
    num_shares = args.num_shares

    # get input file and output file and number of shares from arguments
    # Remove #include directives
    c_file = "test.c"
    ast = parse_file(c_file, use_cpp=True)

    # Create and run the FunctionProcessor
    processor = FunctionProcessor(num_shares= num_shares)
    
    processor.visit(ast)
    processor.save_to_file(ast, c_file)