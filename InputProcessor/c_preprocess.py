# preprocess the c file:
# remove comments, include directives
# use pycparse for the following

# convert the return type the function into void type.
# and add ouput_pointer corresponding to particular fucntion {name_of_function_out* } corresponding to the return value.
# add that result pointer to the parameter list of the function.
# if declaration of int a = 10, or int a = x * z; are present then we need to seprate it like so int a; a = 10; or a = x * z
# convert the if block into assignment statements.
# convert unroll the for loop


# remove the 
import pycparser
import re
import os
from pycparser import c_parser, c_ast, c_generator

class CPreprocessor:
    """
    Preprocess the C file: removes comments, include directives, etc.
    """
    def preprocess(self, file_path):
        with open(file_path, "r") as f:
            c_code = f.read()

        # Remove single-line and multi-line comments
        c_code = re.sub(r"//.*", "", c_code)  # Remove single-line comments
        c_code = re.sub(r"/\*.*?\*/", "", c_code, flags=re.DOTALL)  # Remove multi-line comments
        
        # Remove #include directives
        c_code = re.sub(r"#include\s+[<\"][^>\"]+[>\"]", "", c_code)
        
        return c_code.strip()
    
class IfBlockTransformer(c_ast.NodeVisitor):
    def __init__(self):
        self.generator = c_generator.CGenerator()
        self.temp_var_counter = 0

    def generate_temp_var(self, base_name):
        """ Generate unique temporary variable names """
        self.temp_var_counter += 1
        return f"{base_name}"

    def visit_Compound(self, node):
        """ Traverse Compound block & replace If nodes while visiting child nodes """
        if not node.block_items:
            print("No block items in Compound Node")
            return  #  Prevents NoneType errors

        new_block_items = []
        for stmt in node.block_items:
            # print(f"Processing statement: {stmt.__class__.__name__}")

            if isinstance(stmt, c_ast.If):
                transformed_statements = self.transform_if(stmt)  #  Replace If with transformed statements
                new_block_items.extend(transformed_statements)
            else:
                transformed_stmt = self.visit(stmt)  #  Ensure all statements are visited recursively

                if transformed_stmt is None:
                    # print(f" Warning: `visit()` returned None for {stmt.__class__.__name__}")
                    new_block_items.append(stmt)  #  Keep the original statement if transformation fails
                else:
                    new_block_items.append(transformed_stmt)

        node.block_items = new_block_items  #  Ensure modified AST is retained


    def transform_if(self, node):
        """ Transform If statement into an equivalent assignment-based block """

        # Step 1: Store the condition in a temporary variable
        cond1_var_name = self.generate_temp_var("cond")
        cond1_var = c_ast.ID(cond1_var_name)
        cond1_decl = c_ast.Decl(
            name=cond1_var_name, quals=[], storage=[], funcspec=[],
            type=c_ast.TypeDecl(declname=cond1_var_name, quals=[],
                                type=c_ast.IdentifierType(names=['int']), align=[]),
            init=node.cond, bitsize=None, align=[]
        )

        # Step 2: Store the negation of the condition in another temporary variable
        neg_cond1_var_name = self.generate_temp_var("negCond")
        neg_cond1_var = c_ast.ID(neg_cond1_var_name)
        neg_cond1_decl = c_ast.Decl(
            name=neg_cond1_var_name, quals=[], storage=[], funcspec=[],
            type=c_ast.TypeDecl(declname=neg_cond1_var_name, quals=[],
                                type=c_ast.IdentifierType(names=['int']), align=[]),
            init=c_ast.UnaryOp(op="!", expr=cond1_var), bitsize=None, align=[]
        )

        # Step 3: Extract statements from If block
        assignments = [cond1_decl, neg_cond1_decl]

        if isinstance(node.iftrue, c_ast.Compound):
            statements = node.iftrue.block_items
        else:
            statements = [node.iftrue] if node.iftrue else []

        for stmt in statements:
            if isinstance(stmt, c_ast.Assignment):
                var_name = stmt.lvalue.name
                op = stmt.op

                # convert to simp;e assignment
                if op in {"+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}:
                    new_rvalue = c_ast.BinaryOp(op=op[0], left=c_ast.ID(var_name), right=stmt.rvalue)
                    stmt = c_ast.Assignment(op="=", lvalue=c_ast.ID(var_name), rvalue=new_rvalue)


                # Step 4: Store the original value before modification (temp1)
                temp1_var_name = self.generate_temp_var(f"temp_{var_name}")
                temp1_var = c_ast.ID(temp1_var_name)
                temp1_decl = c_ast.Decl(
                    name=temp1_var_name, quals=[], storage=[], funcspec=[],
                    type=c_ast.TypeDecl(declname=temp1_var_name, quals=[],
                                        type=c_ast.IdentifierType(names=['int']), align=[]),
                    init=c_ast.ID(var_name), bitsize=None, align=[]
                )

                # Step 5: Compute new value (temp2 = cond1 * modified_value)
                temp2_var_name = self.generate_temp_var(f"res_{var_name}")
                temp2_var = c_ast.ID(temp2_var_name)
                temp2_decl = c_ast.Decl(
                    name=temp2_var_name, quals=[], storage=[], funcspec=[],
                    type=c_ast.TypeDecl(declname=temp2_var_name, quals=[],
                                        type=c_ast.IdentifierType(names=['int']), align=[]),
                    init=c_ast.BinaryOp(op="*", left=cond1_var, right=stmt.rvalue), bitsize=None, align=[]
                )

                # Step 6: Compute negated original value (temp1 * negCond1)
                temp1_neg_cond1_var_name = self.generate_temp_var(f"tempIntoNegCond_{var_name}")
                temp1_neg_cond1_var = c_ast.ID(temp1_neg_cond1_var_name)
                temp1_neg_cond1_decl = c_ast.Decl(
                    name=temp1_neg_cond1_var_name, quals=[], storage=[], funcspec=[],
                    type=c_ast.TypeDecl(declname=temp1_neg_cond1_var_name, quals=[],
                                        type=c_ast.IdentifierType(names=['int']), align=[]),
                    init=c_ast.BinaryOp(op="*", left=temp1_var, right=neg_cond1_var), bitsize=None, align=[]
                )

                # Step 7: Compute final value (modified_var = temp2 + temp1NegCond1)
                final_assignment = c_ast.Assignment(
                    op="=", lvalue=c_ast.ID(var_name),
                    rvalue=c_ast.BinaryOp(op="+", left=temp2_var, right=temp1_neg_cond1_var)
                )

                # Store transformed statements
                assignments.extend([temp1_decl, temp2_decl, temp1_neg_cond1_decl, final_assignment])

        #  Return a **list of statements** instead of a `Compound` block
        return assignments

class FunctionTransformer(c_ast.NodeVisitor):
    """ Transform function return types to void and add output pointers """
    def visit_FuncDef(self, node):
        """ Convert function return type to void and add output pointer to parameter list """
        func_name = node.decl.name
        return_type = node.decl.type.type

        if not isinstance(return_type, c_ast.TypeDecl):  # Ignore if already void
            return
        
        # Modify return type to void
        return_type.type.names = ['void']
        
        # Create output pointer
        output_pointer = c_ast.Decl(
            name=f"{func_name}_out",
            quals=[],
            align=[],
            storage=[],
            funcspec=[],
            type=c_ast.PtrDecl(
                quals=[],
                type=c_ast.TypeDecl(
                    declname=f"{func_name}_out",
                    quals=[],
                    align=[],
                    type=c_ast.IdentifierType(names=['int'])  # Assume int return type
                )
            ),
            init=None,
            bitsize=None
        )

        # Add to function parameter list
        if isinstance(node.decl.type.args, c_ast.ParamList):
            node.decl.type.args.params.append(output_pointer)
        else:
            node.decl.type.args = c_ast.ParamList(params=[output_pointer])

        self.modify_return_statements(node.body, func_name)

    def modify_return_statements(self, body, func_name):
        """ Modify return statements to assign value to the output pointer """
        if not isinstance(body, c_ast.Compound):
            return

        new_statements = []
        for stmt in body.block_items:
            if isinstance(stmt, c_ast.Return):
                if stmt.expr is not None:
                    # Replace `return expr;` with `*func_name_out = expr; return;`
                    assign_output = c_ast.Assignment(
                        op="=",
                        lvalue=c_ast.UnaryOp(op="*", expr=c_ast.ID(name=f"{func_name}_out")),
                        rvalue=stmt.expr
                    )
                    new_statements.append(assign_output)
            elif isinstance(stmt, c_ast.Compound):
                # reccursively modify stmt inside nested block
                self.modify_return_statements(stmt, func_name)
                new_statements.append(stmt)

            else:
                new_statements.append(stmt)

        body.block_items = new_statements

    def visit_Compound(self, node):
        """ Apply `IfBlockTransformer` and `DeclarationTransformer` before visiting children """
        if node.block_items:
            self.if_transformer.visit(node)  #  Apply IfBlockTransformer
            self.decl_transformer.visit(node)  #  Apply DeclarationTransformer
            for i, stmt in enumerate(node.block_items):
                node.block_items[i] = self.visit(stmt)  #  Process child nodes
        # return node  #  Ensure the modified node is returned

    def visit_For(self, node):
        """ Ensure if-statements inside for-loops are transformed """
        node.stmt = self.visit(node.stmt)  #  Process loop body
        return node  #  Ensure modified node is returned


class DeclarationTransformer(c_ast.NodeVisitor):
    """ Convert `int a = 10;` into `int a; a = 10;` by modifying the AST in-place """
    
    def visit_Compound(self, node):
        """ Process function body and replace declarations inside it """
        if not node.block_items:
            print("No block items in Compound Node")
            return  #  Prevents NoneType errors

        new_block_items = []  # Store modified statements
        for stmt in node.block_items:
            # print(f"Processing statement: {stmt.__class__.__name__}")  # Debugging statement

            if isinstance(stmt, c_ast.DeclList):
                transformed_stmts = self.transform_multi_declaration(stmt)  # Handle multiple variables
                if transformed_stmts:
                    new_block_items.extend(transformed_stmts)
                else:
                    # print(f"Warning: `transform_multi_declaration` returned None for {stmt}")
                    new_block_items.append(stmt)

            elif isinstance(stmt, c_ast.Decl) and stmt.init:
                transformed_stmts = self.transform_declaration(stmt)  # Replace declaration
                if transformed_stmts:
                    new_block_items.extend(transformed_stmts)
                else:
                    # print(f"Warning: `transform_declaration` returned None for {stmt}")
                    new_block_items.append(stmt)

            elif isinstance(stmt, c_ast.Compound):  
                self.visit(stmt)  # Process nested blocks
                new_block_items.append(stmt)

            else:
                transformed_stmt = self.visit(stmt)  # Ensure recursive visiting of all statements
                if transformed_stmt is not None:
                    new_block_items.append(transformed_stmt)
                else:
                    # print(f" Warning: `visit()` returned None for {stmt.__class__.__name__}")
                    new_block_items.append(stmt)  # Keep original if transformation fails

        node.block_items = new_block_items  #  Modify the AST in place!

    def transform_multi_declaration(self, node):
        """ Handle multiple variable declarations in a single statement """
        transformed_nodes = []
        for decl in node.decls:
            transformed_nodes.extend(self.transform_declaration(decl))
        return transformed_nodes 
    
    def transform_declaration(self, node):
        """ Split declaration into `Decl` + `Assignment` or `FuncCall` transformation """
        if isinstance(node.init, c_ast.FuncCall):
            return self.transform_function_call_declaration(node)  #  Handle function calls
        elif node.init:
            return self.transform_regular_declaration(node)  #  Handle normal assignments
        else:
            return [node]  #  No modification needed

    def transform_regular_declaration(self, node):
        """ Convert `int a = 10;` → `int a; a = 10;` """
        new_decl = c_ast.Decl(
            name=node.name,
            quals=[],
            align=[],
            storage=[],
            funcspec=[],
            type=node.type, init=None, bitsize=None
        )

        assignment = c_ast.Assignment(
            op="=",
            lvalue=c_ast.ID(name=node.name),
            rvalue=node.init
        )

        return [new_decl, assignment]  # Return as a list to replace the old node
    
    def transform_function_call_declaration(self, node):
        """ Convert `int a = fun(b, c);` → `int a; fun(b, c, &a);` """
        func_call = node.init  # The function call (`fun(b, c)`)

        #  Step 1: Create a declaration without initialization (`int a;`)
        new_decl = c_ast.Decl(
            name=node.name,
            quals=[],
            align=[],
            storage=[], funcspec=[],
            type=node.type, init=None, bitsize=None
        )

        #  Step 2: Modify function call to pass `&a` as an extra argument
        output_arg = c_ast.UnaryOp(op="&", expr=c_ast.ID(name=node.name))  # `&a`
        if func_call.args:
            func_call.args.exprs.append(output_arg)  # Add `&a` to argument list
        else:
            func_call.args = c_ast.ExprList(exprs=[output_arg])

        #  Step 3: Create a function call statement (`fun(b, c, &a);`)
        func_stmt = c_ast.FuncCall(name=func_call.name, args=func_call.args)

        return [new_decl, func_stmt]  #  Replace with declaration + function call

# class ForLoopUnroller(c_ast.NodeVisitor):
#     def visit_Compound(self, node):
#         """ Process function body and replace declarations inside it """
#         if not node.block_items:
#             print("No block items in Compound Node")
#             return

#         new_block_items = []  # Store modified statements
#         for stmt in node.block_items:
#             print(f"Processing statement: {stmt.__class__.__name__}")
#             if isinstance(stmt, c_ast.For):
#                 unrolled_stmts = self.unroll_for_loop(stmt)  # Handle multiple variables
#                 if unrolled_stmts:
#                     new_block_items.extend(unrolled_stmts)
#                 else:
#                     print(f"Warning: `unroll_for_loop` returned None for {stmt}")
#                     new_block_items.append(stmt)
#             else:
#                 # visit all other stmts to check for nested for loops
#                 transformed_stmt = self.visit(stmt)
#                 if transformed_stmt is not None:
#                     new_block_items.append(transformed_stmt)
#                 else:
#                     print(f" Warning: `visit()` returned None for {stmt.__class__.__name__}")
#                     new_block_items.append(stmt)
            
#             node.block_items = new_block_items  #  Modify the AST in place!

#     def visit_For(self, node):
#         # replace the for loop with the unrolled version
#         return self.unroll_for_loop(node)

#     def unroll_for_loop(self, node):
#         """ Unroll the for loop into multiple iterations 
#         e.g.,
#             for (int i = 0; i < 10; i++) {
#                 x = i * 2;
#             }
#         becomes:
#             x = 0 * 2;
#             x = 1 * 2;
#             ...
#             x = 9 * 2;

#         """
#         if isinstance(node.init, c_ast.DeclList):
#             # Assuming only one variable is declared in the for loop
#             decl = node.init.decls[0]
#             loop_var = decl.name
#             start_val = decl.init.value if decl.init else None
#         elif isinstance(node.init, c_ast.Decl):
#             loop_var = node.init.name
#             start_val = node.init.init.value if node.init.init else None
#         elif isinstance(node.init, c_ast.Assignment):
#             loop_var = node.init.lvalue.name
#             start_val = node.init.rvalue.value if node.init.rvalue else None
#         else:
#             print("Invalid for loop initialization")
#             return
        
#         if start_val is None:
#             print("Invalid start value for loop variable")
#             return [node]
        
#         if not isinstance(node.cond, c_ast.BinaryOp) or node.cond.op not in ["<", "<=", ">", ">="]:
#             print("cannot unroll the loop condition is not a simple comparison")
#             return [node]


#         if not isinstance(node.next, c_ast.UnaryOp, c_ast.Assignment):
#             # check if the increment is a simple increment or decrement
#             # e.g., i++ or i-- (a unary operation)
#             # or i += 2 or i -= 1 (an assignment operation)
#             print("cannot unroll the loop increment is not a simple increment")
#             return [node]

#         # Extract loop bounds
#         if isinstance(node.next, c_ast.Assignment): # e.g., i += 1
#             if isinstance(node.next.rvalue, c_ast.BinaryOp) and node.next.rvalue.op in ["+", "-"]:
#                 step_val = node.next.rvalue.right.value
#                 step_val = int(step_val) if node.next.rvalue.op == "+" else -(step_val)
#             else:
#                 print("Invalid step value for loop variable")
#                 return [node]
#         elif isinstance(node.next, c_ast.UnaryOp): # case of i++ or i--
#             if node.next.op in ["p++", "++"]:
#                 step_val = 1
#             elif node.next.op in ["p--", "--"]:
#                 step_val = -1

#         stop_val  = node.cond.right.value
#         if not (start_val.isdigit() and stop_val.isdigit() and step_val.isdigit()):
#             print("Cannot unroll the loop as the loop bounds are not constant")
#             return [node]

#         start_val, stop_val = int(start_val), int(stop_val)

#         # store urolled stmts
#         unrolled_statements = []
#         for i in range(start_val, stop_val, step_val): 
#             # replace the loop varible occurrences with i
#             unrolled_body = self.clone_and_replace(node.stmt, loop_var, i)
#             unrolled_statements.extend(unrolled_body)
        
#         return unrolled_statements

#     def clone_and_replace(self, node, loop_var, value):
#         """
#         recursively clone the node and replace the loop variable with the value
#         """
#         if isinstance(node, c_ast.Compound):
#             new_block_items = []
#             for stmt in node.block_items:
#                 new_block_items.extend(self.clone_and_replace(stmt, loop_var, value))
#             return new_block_items

#         elif isinstance(node, c_ast.Assignment):
#             return c_ast.Assignment(
#                 op = node.op,
#                 lvalue = node.lvalue,
#                 rvalue = self.replace_var(node.rvalue, loop_var, value)
#             )
        
#         return node

#     def replace_var(self, expr, loop_var, value):
#         """
#         Replace the loop variable with the value in the expression
#         """
#         if isinstance(expr, c_ast.ID) and expr.name == loop_var:
#             return c_ast.Constant(type="int", value=str(value))
        
#         elif isinstance(expr, c_ast.BinaryOp):
#             return c_ast.BinaryOp(
#                 op = expr.op,
#                 left = self.replace_var(expr.left, loop_var, value),
#                 right = self.replace_var(expr.right, loop_var, value)
#             )
        
#         elif isinstance(expr, c_ast.UnaryOp):
#             return c_ast.UnaryOp(
#                 op = expr.op,
#                 expr = self.replace_var(expr.expr, loop_var, value)
#             )
#         elif isinstance(expr, c_ast.ArrayRef) and isinstance(expr.subscript, c_ast.ID) and expr.subscript.name == loop_var:
#             return c_ast.ArrayRef(
#                 name = expr.name,
#                 subscript = c_ast.Constant(type="int", value=str(value))
#             )

#         elif isinstance(expr, c_ast.FuncCall) and expr.args:
#             new_args = []
#             for arg in expr.args.exprs:
#                 new_args.append(self.replace_var(arg, loop_var, value))
#             return c_ast.FuncCall(
#                 name = expr.name,
#                 args = c_ast.ExprList(exprs=new_args)
#             )
#         return expr
    


"""
Testing for loop unroller class

"""

# import pycparser
# from pycparser import c_parser, c_ast, c_generator


class ForLoopUnroller(c_ast.NodeVisitor):
    def __init__(self):
        self.loop_declared_vars = set()

    def visit_Compound(self, node):
        """ Process function body and replace declarations inside it """
        if not node.block_items:
            print("No block items in Compound Node")
            return

        new_block_items = []  # Store modified statements
        for stmt in node.block_items:
            # print(f"Processing statement: {stmt.__class__.__name__}")
            if isinstance(stmt, c_ast.For):
                unrolled_stmts = self.unroll_for_loop(stmt)  # Handle multiple variables
                if unrolled_stmts:
                    new_block_items.extend(unrolled_stmts)
                else:
                    # print(f"Warning: `unroll_for_loop` returned None for {stmt}")
                    new_block_items.append(stmt)
            else:
                # visit all other stmts to check for nested for loops
                transformed_stmt = self.visit(stmt)
                if transformed_stmt is not None:
                    new_block_items.append(transformed_stmt)
                else:
                    # print(f" Warning: `visit()` returned None for {stmt.__class__.__name__}")
                    new_block_items.append(stmt)
            
            node.block_items = new_block_items  #  Modify the AST in place!

    def visit_For(self, node):
        # replace the for loop with the unrolled version
        return self.unroll_for_loop(node)

    def unroll_for_loop(self, node):
        """ Unroll the for loop into multiple iterations 
        e.g.,
            for (int i = 0; i < 10; i++) {
                x = i * 2;
            }
        becomes:
            x = 0 * 2;
            x = 1 * 2;
            ...
            x = 9 * 2;

        """
        if isinstance(node.init, c_ast.DeclList):
            # Assuming only one variable is declared in the for loop
            decl = node.init.decls[0]
            loop_var = decl.name
            start_val = decl.init.value if decl.init else None
        elif isinstance(node.init, c_ast.Decl):
            loop_var = node.init.name
            start_val = node.init.init.value if node.init.init else None
        elif isinstance(node.init, c_ast.Assignment):
            loop_var = node.init.lvalue.name
            start_val = node.init.rvalue.value if node.init.rvalue else None
        else:
            print("Invalid for loop initialization")
            return
        
        if start_val is None:
            print("Invalid start value for loop variable")
            return [node]
        
        if not isinstance(node.cond, c_ast.BinaryOp) or node.cond.op not in ["<", "<=", ">", ">="]:
            print("cannot unroll the loop condition is not a simple comparison")
            return [node]


        if not isinstance(node.next, (c_ast.UnaryOp, c_ast.Assignment)):
            # check if the increment is a simple increment or decrement
            # e.g., i++ or i-- (a unary operation)
            # or i += 2 or i -= 1 (an assignment operation)
            print("cannot unroll the loop increment is not a simple increment")
            return [node]

        # Extract loop bounds
        if isinstance(node.next, c_ast.Assignment): # e.g., i += 1
            if isinstance(node.next.rvalue, c_ast.BinaryOp) and node.next.rvalue.op in ["+", "-"]:
                step_val = node.next.rvalue.right.value
                step_val = int(step_val) if node.next.rvalue.op == "+" else -(step_val)
            else:
                print("Invalid step value for loop variable")
                return [node]
        elif isinstance(node.next, c_ast.UnaryOp): # case of i++ or i--
            if node.next.op in ["p++", "++"]:
                step_val = 1
            elif node.next.op in ["p--", "--"]:
                step_val = -1

        stop_val  = node.cond.right.value

        if not (start_val.isdigit() and stop_val.isdigit()):
            print("Cannot unroll the loop as the loop bounds are not constant")
            return [node]

        start_val, stop_val = int(start_val), int(stop_val)

        if node.cond.op == "<":  # Stop before stop_val
            stop_val = stop_val  # No change needed
        elif node.cond.op == "<=":  # Include stop_val
            stop_val += 1
        elif node.cond.op == ">":  # Stop before stop_val
            stop_val = stop_val  # No change needed
        elif node.cond.op == ">=":  # Include stop_val
            stop_val -= 1
        # print(f"stop_val : {stop_val} ,start_val : {start_val}" )

        for smt in node.stmt.block_items:
            if isinstance(smt, c_ast.Decl):
                self.loop_declared_vars.add(smt.name) # store the declared variables in the loop

        # store urolled stmts
        unrolled_statements = []
        for i in range(start_val, stop_val, step_val): 
            # replace the loop varible occurrences with i
            unrolled_body = self.clone_and_replace(node.stmt, loop_var, i)
            unrolled_statements.extend(unrolled_body)
        
            # unrolled_statements.append(c_ast.EmptyStatement())  # Add an empty statement to separate loop iterations
        return unrolled_statements

    def clone_and_replace(self, node, loop_var, value):
        """
        recursively clone the node and replace the loop variable with the value
        """
        if isinstance(node, c_ast.Compound):  # If it's a block `{ ... }`
            new_block_items = []
            for stmt in node.block_items:
                new_stmt = self.clone_and_replace(stmt, loop_var, value)
                if isinstance(new_stmt, list):  # Flatten nested lists
                    new_block_items.extend(new_stmt)
                else:
                    new_block_items.append(new_stmt)
            return new_block_items
        
        elif isinstance(node, c_ast.Decl):
            new_type = self.replace_var(node.type, loop_var, value)

            if isinstance(new_type, c_ast.TypeDecl):
                new_type = c_ast.TypeDecl(
                    declname=f"{node.name}_{value}",
                    type=new_type.type,
                    quals=new_type.quals,
                    align=new_type.align,
                    coord=new_type.coord
                )

            new_decl = c_ast.Decl(
                name = f"{node.name}_{value}",
                quals = node.quals,
                align= node.align,
                storage = node.storage,
                funcspec = node.funcspec,
                type = new_type,
                init = self.replace_var(node.init, loop_var, value) if node.init else None,
                bitsize = node.bitsize
            )
            return new_decl
        elif isinstance(node, c_ast.Assignment):
            return c_ast.Assignment(
                op = node.op,
                lvalue = self.replace_var(node.lvalue, loop_var, value),
                rvalue = self.replace_var(node.rvalue, loop_var, value)
            )
        
        return node

    def replace_var(self, expr, loop_var, value):
        """
        Replace the loop variable with the value in the expression
        """
        if isinstance(expr, c_ast.ID):
            if expr.name == loop_var:
                return c_ast.Constant(type="int", value=str(value))
            elif expr.name in self.loop_declared_vars:
                return c_ast.ID(name=f"{expr.name}_{value}")
            else:
                return expr
        
        elif isinstance(expr, c_ast.TypeDecl):
            return c_ast.TypeDecl(
                declname = f"{expr.declname}_{value}" if expr.declname else None,
                quals = expr.quals,
                align = expr.align,
                type = expr.type,
                coord = expr.coord
            )
            

        elif isinstance(expr, c_ast.Constant):
            return expr
        
        elif isinstance(expr, c_ast.BinaryOp):
            return c_ast.BinaryOp(
                op = expr.op,
                left = self.replace_var(expr.left, loop_var, value),
                right = self.replace_var(expr.right, loop_var, value)
            )
        
        elif isinstance(expr, c_ast.UnaryOp):
            return c_ast.UnaryOp(
                op = expr.op,
                expr = self.replace_var(expr.expr, loop_var, value)
            )
        
        elif isinstance(expr, c_ast.ArrayRef) and isinstance(expr.subscript, c_ast.ID) and expr.subscript.name == loop_var:
            return c_ast.ArrayRef(
                name = expr.name,
                subscript = c_ast.Constant(type="int", value=str(value))
            )

        elif isinstance(expr, c_ast.FuncCall) and expr.args:
            new_args = []
            for arg in expr.args.exprs:
                new_args.append(self.replace_var(arg, loop_var, value))
            return c_ast.FuncCall(
                name = expr.name,
                args = c_ast.ExprList(exprs=new_args)
            )
        return expr


        
# c_code = """
# int G256_newbasis(int x, int b[]) {
#   int i, y = 0;


#   for (i = 7; i >= 0; i--) {
#     if (x & 1)
#       y ^= b[i];
#     x >>= 1;
#   }
#   return y;
# }
# """

# parser = c_parser.CParser()
# ast = parser.parse(c_code)
# ast.show()
# from pycparser import parse_file
# c_file = "test.c"
# ast = parse_file(c_file, use_cpp=True)
# ast.show()
# # Step 3: Transform the AST
# transformer = IfBlockTransformer()
# transformer.visit(ast)  # Replace If nodes inside Compound blocks


# # Step 2: Apply FunctionTransformer
# # transformer = FunctionTransformer()
# # transformer.visit(ast)
# # ast.show()
# print("----------------------")
# print("Transformed AST after declaration transformer:")

# # Step 3: Apply DeclarationTransformer
# declaration_transformer = DeclarationTransformer()
# declaration_transformer.visit(ast)
# # ast.show()

# # Step 4: Apply ForLoopUnroller
# unroller = ForLoopUnroller()
# unroller.visit(ast)
# # ast.show()

# # Step 5: Regenerate the transformed C code
# generator = c_generator.CGenerator()
# transformed_code = generator.visit(ast)
# print(transformed_code)

# # # convert the modified to code into three address code 
# # # also move the declaration above at the beginning of the function