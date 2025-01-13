import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The class now processes unary operators correctly but does not handle ternary operators.
 */
public class ThreeAddressCodeGenerator {

    private int tempCounter = 0; // Counter for generating temporary variables
    private List<String> instructions = new ArrayList<>(); // Stores TAC instructions
    private Map<String, String> expressionCache = new HashMap<>();
    List<String> delayedInstructions = new ArrayList<>();
    public int getDom_count() {
        return dom_count;
    }

    int dom_count;
    /**
     * Inner class to represent a token.
     */
    private static class Token {
        enum Type { OPERAND, OPERATOR, PARENTHESIS, UNKNOWN }

        private final String value;
        private final Type type;
//        private final boolean isUnary;

        public Token(String value, Type type) {
            this.value = value;
            this.type = type;
        }

        public String getValue() {
            return value;
        }

        public Type getType() {
            return type;
        }

        public boolean isOperand() {
            return type == Type.OPERAND;
        }

        public boolean isOperator() {
            return type == Type.OPERATOR;
        }

        public boolean isParenthesis() {
            return type == Type.PARENTHESIS;
        }

        public static Token fromString(String str) {
            if (str.matches("[a-zA-Z_][a-zA-Z0-9_]*|\\d+|\\b0[xX][0-9a-fA-F]+\\b")) {
                return new Token(str, Type.OPERAND);
            } else if (str.matches("[-+*/%&|^<>=]=?|<<=?|>>=?|&&|\\|\\||[-+~]|\\+\\+|--")) {
                return new Token(str, Type.OPERATOR);
            } else if (str.equals("(") || str.equals(")")) {
                return new Token(str, Type.PARENTHESIS);
            } else {
                return new Token(str, Type.UNKNOWN);
            }
        }

        @Override
        public String toString() {
            return "{" +
                     value +
                    '}';
        }
    }


    /**
     * Generates a new temporary variable.
     */
    private String newTemp() {
        return "t" + (++tempCounter);
    }

    private void clearCache() {
        expressionCache.clear();
    }

    /**
     * Emits a Three-Address Code instruction.
     */
    private void emit(String operation, String arg1, String arg2, String result) {

        if(operation.endsWith("u")){
            operation = operation.substring(0, operation.length()-1);
        }
        if (operation.equals("&")){
            String hexPattern = "^0[xX][0-9a-fA-F]+$";
            String decimalPattern = "^-?\\d+$";

            // increment dom count if the both argument of & are variables

            if(!arg1.matches(hexPattern) && !arg1.matches(decimalPattern) && !arg2.matches(hexPattern) && !arg2.matches(decimalPattern)){
                dom_count++;
            }
        }
        // Create the expression string
        String expression = (arg2 == null) ? operation + " " + arg1 : arg1 + " " + operation + " " + arg2;

        // Optimize for common subexpression
        if (expressionCache.containsKey(expression)) {
            // Reuse the previously computed result
            String cachedResult = expressionCache.get(expression);
            if (!result.equals(cachedResult)) {
                instructions.add(result + " = " + cachedResult); // Direct assignment
            }
//            lastExpression = expression;
//            lastAssignedVariable = cachedResult;
        } else {
            // Emit a new instruction
            if (arg2 == null) {
                instructions.add(result + " = " + operation + " " + arg1); // Unary operation
            } else {
                instructions.add(result + " = " + arg1 + " " + operation + " " + arg2); // Binary operation
            }

            // Cache the expression and result
//            expressionCache.put(expression, result);
//            lastExpression = expression;
//            lastAssignedVariable = result;
        }
    }


    /**
     * Translates a function body into Three-Address Code (TAC).
     */
    public void translateToTAC(String functionBody) {
        // Remove variable declarations
        functionBody = preprocessDeclarations(functionBody);

        // Split the function body into individual statements
        String[] statements = functionBody.split(";");

        for (String statement : statements) {
            statement = statement.trim();
            if (statement.isEmpty()) continue;
            // new independent statement
//            clearCache();
            if (statement.startsWith("return")) {
                // Handle return statements
                String returnValue = statement.replace("return", "").trim();
                String result = parseExpression(returnValue, null);
                instructions.add("return value :  " + result);
            }// Handle pointer declarations
            else if (statement.matches("(int|float|double|char|short|long|unsigned|signed)\\s*\\*\\s*[a-zA-Z_][a-zA-Z0-9_]*\\s*(=.*)?")) {
                processPointerDeclaration(statement);
            }
            else if (statement.matches(".+=.+")) { // Match assignment or compound assignment
                processAssignment(statement);
            } else if(statement.startsWith("++") || statement.startsWith("--")){
                parseExpression(statement, null);
            }
            else if(statement.endsWith("++") || statement.endsWith("--")){
                parseExpression(statement, null);
            }
        }
    }

    /**
     * Processes an assignment statement, including compound assignments.
     */
    private void processAssignment(String statement) {
        // Match compound assignment operators
        Pattern compoundPattern = Pattern.compile("(.+)(\\+=|-=|\\*=|/=|%=|&=|\\|=|\\^=|<<=|>>=)(.+)");
        Matcher matcher = compoundPattern.matcher(statement);

        if (matcher.matches()) {
            String lhs = matcher.group(1).trim(); // Left-hand side (variable being assigned)
            String operator = matcher.group(2).trim(); // Compound operator (e.g., +=)
            String rhs = matcher.group(3).trim(); // Right-hand side (expression)

            // Decompose compound assignment (e.g., a += b -> a = a + b)
            String simpleOperator = operator.substring(0, operator.length() - 1); // Extract base operator (e.g., +, -, etc.)
            String result = parseExpression(lhs + " " + simpleOperator + " " + rhs, lhs); // Parse the equivalent binary expression
            instructions.add(lhs + " = " + result); // Emit assignment instruction
        } else if(statement.matches(".+=.+")){
            // Handle simple assignments
            String[] parts = statement.split("=");
            String lhs = parts[0].trim(); // Left-hand side (variable being assigned)
            String rhs = parts[1].trim(); // Right-hand side (expression)
//            System.out.println("RHS: "+rhs);
            // check for pre-increment/decrement (e.g., ++x, --x)
            if(rhs.matches("(\\+\\+|--)[a-zA-Z_][a-zA-Z0-9_]*")){
                String operator = rhs.substring(0,2); // extract operator (++ or --)
                String variable = rhs.substring(2).trim(); // extract variable name (++var)
                String temp = newTemp(); // Temporary variable for incremented value
                emit("+", variable, "1", temp); // generates the TAC for the operation
                instructions.add(lhs + " = " + temp);
            }else if(rhs.matches("[a-zA-Z_][a-zA-Z0-9_]*(\\+\\+|--)")){

                String variable = rhs.substring(0, rhs.length() - 2).trim(); // extract the variable name
                String operator = rhs.substring(rhs.length()-2); // extract post inc/dec operator (x++ or x--)
                String temp = newTemp(); // Temporary variable for the original value
                instructions.add(lhs + " = " + variable);
                emit("+", variable, "1", variable); // increment the variable
            }else {
                // handle simple assignment expression (x = y + z)
                String result = parseExpression(rhs, lhs);
//                System.out.println("parsing the expression : "+rhs);
//                if (lastAssignedVariable != null && result.equals(lastAssignedVariable)) {
//                    instructions.add(lhs + " = " + lastAssignedVariable); // Direct assignment
//                } else {
//                    instructions.add(lhs + " = " + result); // Emit standard assignment
//                }
//
//                lastAssignedVariable = lhs; // Update tracking for optimization
//                lastExpression = rhs;
                if (!result.equals(lhs)) {
                    instructions.add(lhs + " = " + result); // Emit assignment only if necessary
                }
            }
        }

    }

    /**
     * Parses an expression and generates TAC instructions.
     */
    private String parseExpression(String expression, String resultVar) {
        Stack<String> operands = new Stack<>();
        Stack<Token> operators = new Stack<>();

        // regex token pattern
//       String tokenPattern = "|\\b0[xX][0-9a-fA-F]+\\b\\+\\+|--|==|!=|<=|>=|\\+=|-=|\\*=|/=|%=|&=|\\|=|\\^=|<<=|>>=|&&|\\|\\||<<|>>|[-+*/%&|^<>=()~\\[\\]?:]|[a-zA-Z_][a-zA-Z0-9_]*|\\d+";
        String tokenPattern = "\\b0[xX][0-9a-fA-F]+\\b|[a-zA-Z_][a-zA-Z0-9_]*|\\+\\+|--|==|!=|<=|>=|\\+=|-=|\\*=|/=|%=|&=|\\|=|\\^=|<<=|>>=|&&|\\|\\||<<|>>|[-+*/%&|^<>=()~\\[\\]?:]|\\d+";

        Pattern pattern = Pattern.compile(tokenPattern);
        Matcher matcher = pattern.matcher(expression);

        Token prevToken = null;

        while (matcher.find()) {
            String tokenStr = matcher.group().trim();
//            System.out.println("[processing token...]\n"+tokenStr);
            if (tokenStr.isEmpty()) continue;

            Token token = Token.fromString(tokenStr);

            if (token.isOperand()) {
                operands.push(token.getValue());
                prevToken = token;
            } else if (token.isOperator()) {
                // Handle Postfix Increment/Decrement (e.g., b++)
                if (prevToken != null && prevToken.isOperand() && (token.getValue().equals("++") || token.getValue().equals("--"))) {
                    System.out.println("yo here");
                    String variable = operands.pop();
                    String temp = newTemp();
                    // if the operator exist after the postfix then
                    instructions.add(temp + " = " + variable); // Store original value
                    delayedInstructions.add(variable + " = " + variable + " " + token.getValue().substring(0, 1) + " 1"); // Increment/Decrement the variable
//                    System.out.println(instructions.getLast());
                    operands.push(temp); // Push original value to stack
                    token = Token.fromString(temp);
                    prevToken = token;
                }
                // Handle Prefix Increment/Decrement (e.g., ++x, --x)
                else if ((token.getValue().equals("++") || token.getValue().equals("--"))
                        && (prevToken == null || prevToken.isOperator() || (prevToken.isParenthesis() && prevToken.getValue().equals("(")))) {
                    if (!matcher.find()) {
                        throw new IllegalArgumentException("Invalid operand after prefix operator: " + token.getValue());
                    }
                    String nextOperand = matcher.group().trim(); // Look ahead for operand
                    if (!nextOperand.matches("[a-zA-Z_][a-zA-Z0-9_]*")) {
                        throw new IllegalArgumentException("Invalid operand after prefix operator: " + token.getValue());
                    }
                    String temp = newTemp();
                    emit(token.getValue().substring(0, 1), nextOperand, "1", nextOperand); // Increment/Decrement the operand
                    operands.push(nextOperand); // Push updated operand to stack
//                    String operator = token.getValue();
//                    operands.push(nextOperand);
//                    processOperation(operands, operator);
                    prevToken = Token.fromString(nextOperand);
                } else {
                    // handling unary
                    if (token.getValue().equals("~")
                            && (prevToken == null || prevToken.isOperator() || (prevToken.isParenthesis() && prevToken.getValue().equals("(")))) {
                        if (!matcher.find()) {
                            throw new IllegalArgumentException("Invalid operand after bitwise NOT operator: " + token.getValue());
                        }
                        String nextOperand = matcher.group().trim();
                        if (!nextOperand.matches("[a-zA-Z_][a-zA-Z0-9_]*|\\d+")) {
                            throw new IllegalArgumentException("Invalid operand after bitwise NOT operator: " + token.getValue());
                        }
//                        String temp = newTemp();
//                        emit("~", nextOperand, null, temp); // Emit TAC for bitwise NOT
//                        operands.push(temp); // Push the result to the stack
                        String operator = token.getValue();
//                        System.out.println("[currently processing :]"+ operator);
                        operands.push(nextOperand);
                        processOperation(operands, operator, resultVar);
                        prevToken = Token.fromString(nextOperand);}
                    else if (prevToken == null || prevToken.isOperator() || (prevToken.isParenthesis() && prevToken.getValue().equals("("))) {
                        // handle unary operators
                        String operator = token.getValue() +"u";
                        if (token.getValue().equals("*")|| token.getValue().equals("&") || token.getValue().equals("+") || token.getValue().equals("-")) {
                            // unary + or -
                            String nextOperand = matcher.find() ? matcher.group() : null;
                            if (nextOperand == null || !nextOperand.matches("[a-zA-Z][a-zA-Z0-9_]*|\\d+")) {
                                throw new IllegalArgumentException("Invalid unary operator: " + token.getValue());
                            }
//                            String temp = newTemp();
//                            emit(operator, nextOperand, null, temp);
                            operands.push(nextOperand);
                            processOperation(operands, operator, resultVar);
                            prevToken = Token.fromString(nextOperand);
                        }
                    } else {
                        // Handle binary operators
                        while (!operators.isEmpty() && (
                                (associativity(token.getValue()).equals("L") && precedence(operators.peek().getValue()) >= precedence(token.getValue())) ||
                                        (associativity(token.getValue()).equals("R") && precedence(operators.peek().getValue()) > precedence(token.getValue()))
                        )) {
                            processOperation(operands, operators.pop().getValue(), resultVar);
                        }
                        operators.push(token);
                        prevToken = token;
                    }
                }
            } else if (token.isParenthesis()) {
                if (token.getValue().equals("(")) {
                    operators.push(token);
                } else if (token.getValue().equals(")")) {
                    while (!operators.isEmpty() && !operators.peek().getValue().equals("(")) {
                        processOperation(operands, operators.pop().getValue(), resultVar);
                    }
                    if (operators.isEmpty() || !operators.peek().getValue().equals("(")) {
                        throw new IllegalArgumentException("Mismatched parentheses in expression: " + expression);
                    }
                    operators.pop();
                }
                prevToken = token;
            }

//            System.out.println("Processed token: " + tokenStr);
//            System.out.println("Operands stack: " + operands);
//            System.out.println("Operators stack: " + operators);
        }

        while (!operators.isEmpty()) {
            Token op = operators.pop();
            if (op.getValue().equals("(")) {
                throw new IllegalArgumentException("Mismatched parentheses in expression: " + expression);
            }
            processOperation(operands, op.getValue(), resultVar);
        }
        for (String instr : delayedInstructions) {
            instructions.add(instr);
        }
        delayedInstructions.clear(); // Clear the delayed instructions


        if (operands.size() != 1) {
            throw new IllegalArgumentException("Invalid syntax: Expression parsing resulted in incorrect operands.");
        }

        return operands.pop();
    }


    /**
     * Processes a single operation and generates TAC.
     */
    private void processOperation(Stack<String> operands, String operator, String result) {
        String expression; // Cache key for the expression
        String temp; // Temporary variable for the result

        if (operator.endsWith("u") || operator.equals("~")) { // Handle unary operators
            if (operands.isEmpty()) {
                throw new IllegalArgumentException("Invalid syntax: Not enough operands for unary operator '" + operator + "'.");
            }

            String operand = operands.pop();
            expression = operator + " " + operand; // Key for unary operation

            // Check for common subexpression
            if (expressionCache.containsKey(expression)) {
                operands.push(expressionCache.get(expression)); // Reuse existing temporary variable
            } else {
                if (result != null) {
                    emit(operator, operand, null, result);
                    operands.push(result);
                } else {
                    temp = newTemp(); // Generate new temporary variable
                    emit(operator, operand, null, temp);
                    expressionCache.put(expression, temp); // Cache the result
                    operands.push(temp);
                }
            }
        } else { // Handle binary operators
            if (operands.size() < 2) {
                throw new IllegalArgumentException("Invalid syntax: Not enough operands for binary operator '" + operator + "'.");
            }

            String operand2 = operands.pop();
            String operand1 = operands.pop();
            expression = operand1 + " " + operator + " " + operand2; // Key for binary operation

            // Check for common subexpression
            if (expressionCache.containsKey(expression)) {
                operands.push(expressionCache.get(expression)); // Reuse existing temporary variable
            } else {
                temp = result != null ? result : newTemp(); // Generate new temporary variable
                emit(operator, operand1, operand2, temp); // Emit TAC for binary operation
                expressionCache.put(expression, temp); // Cache the result
                operands.push(temp);
            }
        }
    }


    /**
     * Determines the precedence of an operator.
     */
    private int precedence(String operator) {
        return switch (operator) {
            case "++", "--" -> 15;  // Post-increment/decrement
            case "~", "*u", "&u", "+u", "-u" -> 14;  // Unary operators (bitwise NOT, dereference, etc.)
            case "*", "/", "%" -> 13;  // Multiplicative
            case "+", "-" -> 12;  // Additive
            case "<<", ">>" -> 11;  // Shift
            case "<", "<=", ">", ">=" -> 10;  // Relational
            case "==", "!=" -> 9;  // Equality
            case "&" -> 8;  // Bitwise AND
            case "^" -> 7;  // Bitwise XOR
            case "|" -> 6;  // Bitwise OR
            case "&&" -> 5;  // Logical AND
            case "||" -> 4;  // Logical OR
            case "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=" -> 3;  // Assignment operators
            default -> -1;  // Lowest precedence (unknown operators)
        };
    }
    private String associativity(String operator) {
        return switch (operator) {
            case "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=" -> "R"; // Right-to-left
            case "++", "--", "~", "*u", "&u", "+u", "-u" -> "R"; // Unary operators
            default -> "L"; // Left-to-right for all others
        };
    }



    /**
     * Preprocesses the function body to remove variable declarations.
     */
    private String preprocessDeclarations(String functionBody) {
        String[] lines = functionBody.split("\\n");
        StringBuilder processedBody = new StringBuilder();

        for (String line : lines) {
            line = line.trim();

            // Match variable declarations with assignments
            if (line.matches("(int|float|double|char|short|long|unsigned|signed)\\s+[a-zA-Z_][a-zA-Z0-9_]*\\s*=.+;")) {
                processedBody.append(line.replaceFirst("(int|float|double|char|short|long|unsigned|signed)\\s+", "")).append("\n");
            } else if (!line.matches("(int|float|double|char|short|long|unsigned|signed)\\s+[a-zA-Z_][a-zA-Z0-9_]*\\s*;")) {
                // Skip pure declarations but include all other lines
                processedBody.append(line).append("\n");
            }
        }
        return processedBody.toString();
    }
    private void processPointerDeclaration(String statement) {
        String[] parts = statement.split("=");
        String lhs = parts[0].trim(); // e.g., "int* ptr"
        String rhs = parts.length > 1 ? parts[1].trim() : null; // Right-hand side (if initialized)

        String type = lhs.split("\\*")[0].trim(); // Extract type, e.g., "int"
        String pointer = lhs.split("\\*")[1].trim(); // Extract pointer variable, e.g., "ptr"

        if (rhs != null) {
            String result = parseExpression(rhs, lhs); // Parse the initialization expression
            instructions.add(pointer + " = " + result); // Emit TAC for initialization
        } else {
            instructions.add(pointer + " = null"); // Default initialization for uninitialized pointers
        }
    }



    /**
     * Prints the generated TAC instructions.
     */
    public void printInstructions() {
        for (String instruction : instructions) {
            System.out.println(instruction);
        }
    }



    public static void main(String[] args) {
        ThreeAddressCodeGenerator generator = new ThreeAddressCodeGenerator();

        // Example function body
        String functionBody = """
                a = (x & 0x2) >> 1;
                b = (x & 0x1);
                c = (y & 0x2) >> 1;
                d = (y & 0x1);
                e = (a ^ b) & (c ^ d);
                p = (a & c) ^ e;
                q = (b & d) ^ e;
                y = x++;
               """;

        generator.translateToTAC(functionBody);
        generator.printInstructions();
        System.out.println("Number of domand required : "+ generator.getDom_count());
    }
}
