from pycparser import c_ast , c_parser

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

    def visit_ArrayRef(self, node):
        """Generate TAC for array references."""
        return node
    
    # def visit_Compound(self, node):
    #     return node

    # def visit(self, node):
    #     """ Dispatch visitor function based on node type """
    #     if isinstance(node, c_ast.BinaryOp):
    #         return self.visit_BinaryOp(node)
    #     elif isinstance(node, c_ast.Constant):
    #         return node.value  # Return constant values directly
    #     elif isinstance(node, c_ast.ID):
    #         return node.name  # Return variable names directly
    #     elif isinstance(node, c_ast.Assignment):
    #         return self.visit_Assignment(node)  # Handle assignments
    #     elif isinstance(node, c_ast.UnaryOp):  # 🔹 Fix: Handle Unary Operators
    #         operator = node.op
    #         operand = self.visit(node.expr)  # Recursively visit the operand
    #         return f"{operator}{operand}"  # Generate correct TAC format
    #     elif isinstance(node, c_ast.Compound):
    #         for stmt in node.block_items: 
    #             print(f"stmt of compound blk:\n {type(node).__name__}{stmt}") 
    #             self.visit(stmt)  # Recursively process each statement
    #         return 
    #     elif isinstance(node, c_ast.FuncCall):
    #         func_name = node.name.name
    #         args = [self.visit(arg) for arg in node.args.exprs] if node.args else []
    #         return f"{func_name}({', '.join(args)})"
    #     # else:
    #         # raise NotImplementedError(f"Unhandled AST Node: {type(node).__name__}")


    def visit_Assignment(self, node):
        """Generate TAC for assignment statements."""
        if isinstance(node.lvalue, c_ast.ID):
            lvalue = node.lvalue.name
        elif isinstance(node.lvalue, c_ast.UnaryOp) and node.lvalue.op == '*':
            # does not handle pointer assign like for e.g. 
            lvalue = f"*{self.visit(node.lvalue.expr)}"
        else:
            raise NotImplementedError(f"Unhandled lvalue type: {type(node.lvalue)}")

        # handle compound assignment operators like +=, -=, etc.
        if node.op in {">>=", "<<=", "+=", "-=", "*=", "/=", "&=", "|=", "^="}:  # Compound assignment
            expanded_rhs = c_ast.BinaryOp(
                op=node.op[:-1],  # Convert `>>=` to `>>`, `+=` to `+`, etc.
                left=node.lvalue,
                right=node.rvalue
            )
            node.op = "="  # Convert `>>=` to `=`
            node.rvalue = expanded_rhs  # Assign the new expanded expression
        
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
            print(f"DEBUG: {lvalue} = {func_name}({', '.join(args)});")
            self.tac.append(f"{lvalue} = {func_name}({', '.join(args)});")
        elif isinstance(node.rvalue, c_ast.UnaryOp):
            operator = node.rvalue.op

            operand = self.visit(node.rvalue.expr)
            
            if operator == "!":
                rhs = f"!{operand}"  # Logical NOT operation
            elif operator == "-":
                rhs = f"-{operand}"  # Negation
            elif operator == "&":
                rhs = f"&{operand}"  # Address-of
            elif operator == "*":
                rhs = f"*{operand}"  # Dereference
            elif operator == "~":
                rhs = f"~{operand}" 
            else:
                raise NotImplementedError(f"Unsupported unary operator: {operator}")
            self.tac.append(f"{lvalue} = {rhs}")  
        else:
            rhs = self.visit(node.rvalue)
            self.tac.append(f"{lvalue} = {rhs}")


    def visit_BinaryOp(self, node, target_var=None, var_type="int"):
        """TAC for binary operations with function calls, avoiding duplicate function calls."""
        # If target_var is provided, use it for the final result
        result_var = target_var if target_var else self.new_temp(var_type)

        # handling of & operator
        if node.op == "&":
            def extract_and_chains(node):
                # recursively extract '&' chians and enforce operand limit = 3
                if isinstance(node, c_ast.BinaryOp) and node.op == "&":
                    left_chain = extract_and_chains(node.left)
                    right_chain = extract_and_chains(node.right)
                    full_chain = left_chain + right_chain
                    # print(f"printing full chain\n:  {full_chain}")
                    if len(full_chain) > 3:
                        raise ValueError(f"Error: '&' operation chain contains {len(full_chain)} operands! only 2 and 3 input and is allowed.")
                    return full_chain
                return [node]
            and_chain  = extract_and_chains(node)
            tac_operands = []
            for operand in and_chain:
                if isinstance(operand, c_ast.UnaryOp):
                    operands = operand.expr.name if isinstance(operand.expr, c_ast.ID) else self.visit(operand.expr)
                    tac_operands.append(f"{operand.op}{operands}")
                else:
                    tac_operands.append(self.visit(operand))
            # print(f"and_chain {and_chain}")
            # print(tac_operands)
            
            # generate TAC for '&' operations
            if len(tac_operands) == 2:
                self.tac.append(f"{result_var} = {tac_operands[0]} & {tac_operands[1]}")
            elif len(tac_operands) == 3:
                self.tac.append(f"{result_var} = {tac_operands[0]} & {tac_operands[1]} & {tac_operands[2]}")
            
            
            return result_var    
        # Process left operand
        if isinstance(node.left, c_ast.FuncCall):
            left = self.visit_FuncCall(node.left, target_var=result_var)  # Reuse target_var
        else:
            left = self.visit(node.left)

        # Process right operand

        
        if isinstance(node.right, c_ast.FuncCall):
            right = self.visit_FuncCall(node.right)  # Create a temp only if needed
        elif isinstance(node.right, c_ast.ArrayRef):
            right = self.visit(node.right)
            right = f"{self.visit(node.right.name)}[{self.visit(node.right.subscript)}]"
        else:
            right = self.visit(node.right)

        # Generate TAC for the binary operation
        self.tac.append(f"{result_var} = {left} {node.op} {right}")

        return result_var

    def visit_FuncCall(self, node, target_var=None):
        """function call handling: reuse target_var when possible."""
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



def test_tac_generator():
    parser = c_parser.CParser()
    tac_gen = TACGenerator()

    test_cases = [
        ("x = a & b;", True),      
        ("x = a & b & ~c;", True), 
        ("x = a & b & c & d;", False),  
        ("x = (a & b) ^ (c & d);", True), 
        ("x = (a & b & c) ^ (d & e);", True), 
        ("x = (a & b & c & d) ^ e;", False), 
        ("x = a + b * c;", True),
    ]

    for expr, should_pass in test_cases:
        print(f"\ntesting: {expr}")
        tac_gen.tac.clear()
        try:
            ast = parser.parse(f"int main() {{ {expr} }}")
            stmt = ast.ext[0].body.block_items[0]
            tac_gen.visit(stmt)

            if should_pass:
                print("passed")
                print("generated TAC:")
                for tac in tac_gen.tac:
                    print(f" {tac}")
                
            else:
                print("excpected error but passed!")

        except  ValueError as e:
            if not should_pass:
                print(f"correctly raised error : {e}")
            else:
                print(f"unexpected error : {e}")


if __name__ == "__main__":
    test_tac_generator()