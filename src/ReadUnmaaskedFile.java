import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ReadUnmaaskedFile {
    private static int count = 0;



    //    private HashMap<Integer,String> functions;
    private HashMap <Integer,FunctionInfo> functionInfo;

    // constructor
    public ReadUnmaaskedFile() {
//        this.functions = new HashMap<>();
        this.functionInfo = new HashMap<>();
    }

    public HashMap<Integer, FunctionInfo> getFunctionInfo() {
        return functionInfo;
    }
    /**
     * reads the C *compilable* file
     * Extract functions form it
     * store them into instance variable functions
     *
     */
    public void  extractFunctionsWithBodies(String filePath) throws IOException {


        // Modular regex for complete function definition

        String returnType = "\\b(void|int|float|double|char|short|long|unsigned|signed|struct\\s+[a-zA-Z_][a-zA-Z0-9_]*|union|enum)\\b";
        String functionName = "[a-zA-Z_][a-zA-Z0-9_]*";
        String parameterType = "(unsigned|signed|int|float|double|char|short|long|struct\\s+[a-zA-Z_][a-zA-Z0-9_]*|union|enum)";
        String parameter = "\\s*" + parameterType + "\\s*\\*?\\s*[a-zA-Z_][a-zA-Z0-9_]*(\\s*\\[\\s*\\])?";
        String parameterList = "(void|(" + parameter + "(\\s*,\\s*" + parameter + ")*))";
        String functionSignature = returnType + "\\s+" + functionName + "\\s*\\(" + parameterList + "\\)";
        String functionBody = "\\{(?:[^{}]*|\\{[^{}]*\\})*\\}";
        String completeFunctionPattern = functionSignature + "\\s*" + functionBody;

        try {
            // Read the entire file content
            String content = Files.readString(Path.of(filePath));

            // Compile the regex pattern
            Pattern pattern = Pattern.compile(completeFunctionPattern);
            Matcher matcher = pattern.matcher(content);

            // Find all matches
            while (matcher.find()) {
                // Get the full function as the entire match
                String fullFunction = matcher.group().trim();
//                this.functions.put(++count,fullFunction);
//                this.functionInfo.put(new FunctionInfo())
                this.processFunction(++count, fullFunction);
            }
        } catch (IOException e) {
            System.out.println("Error reading the file: " + e.getMessage());
        }

    }


    /**
     * print all the function extracted from the files
     * print the function Info for each function
     *
     */
    void printAllFunctions(){
        functionInfo.forEach((key, value) -> value.printFunctionInfo());
    }

    /**
     * process the function and extract its argument variables and local variable
     *
     */

    public static Integer getFunctionsCount(){
        return count;
    }

    /**
     * ===========================
     * Valid C Parameter Declarations
     * ===========================

    * 1. Basic Data Types
    void basicTypes(int a, float b, char c, double d);

    * 2. Pointers
    void pointerParameter(int *ptr, float *fptr, char **strPtr);

    * 3. Arrays (passed as pointers)
    void arrayParameter(int arr[]);         // Single-dimensional array
    void arrayWithSize(int arr[10]);       // Array with fixed size
    void multidimensionalArray(int arr[][10]); // Multidimensional array with inner size

    * 4. Structures
    struct Point {
        int x;
        int y;
    };
    void structByValue(struct Point p);    // Pass structure by value
    void structByReference(struct Point *p); // Pass structure by reference

    * 5. Typedef
    typedef unsigned int uint;
    void typedefParameter(uint a);        // Typedef alias for unsigned int

    * 6. Enumerations
    enum Color { RED, GREEN, BLUE };
    void enumParameter(enum Color color); // Pass enum as parameter

    * 7. Function Pointers
    void functionPointer(int (*func)(int, int)); // Function pointer as parameter

    * 8. Void Parameters
    void noParameters(void);              // Function with no parameters
    void genericPointer(void *data);      // Void pointer (generic data)

    * 9. Qualifiers (const, volatile)
    void qualifiedParameters(const int a, volatile int *b); // Constant and volatile qualifiers

    * 10. Mixed Types
    void mixedParameters(int a, float *b, char c[], struct Point *p);

    * 11. Arrays with Static Size in Declaration (C99 and later)
    void staticSizedArray(int arr[static 10]); // Minimum size constraint for the array

    * 12. Pointers to Arrays
    void pointerToArray(int (*arr)[10]);   // Pointer to an array of 10 integers

    * 13. Pointers to Functions
    void pointerToFunction(int (*func)(int, int)); // Function pointer

    * 14. Pointers to Structures
    void pointerToStruct(struct Point *p); // Pointer to a structure

    * 15. Inline Arrays
    void inlineArray(int arr[10]);         // Inline array declaration

    * 16. Pointers to Void
    void pointerToVoid(void *data);

    */


    private void processFunction(int key,String fullFunction) {
        String signatureRegex = "\\b(void|int|float|double|char|short|long|unsigned|signed|struct\\s+[a-zA-Z_][a-zA-Z0-9_]*|union|enum)\\b" +
                "\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*" +
                "\\(([^)]*)\\)\\s*\\{";
        Pattern signaturePattern = Pattern.compile(signatureRegex);
        Matcher signatureMatcher = signaturePattern.matcher(fullFunction);

        if (signatureMatcher.find()) {
            String returnType = signatureMatcher.group(1); // Return type
            String functionName = signatureMatcher.group(2); // Function name
            String parameterList = signatureMatcher.group(3); // Parameters

            FunctionInfo functionInfo = new FunctionInfo(functionName, returnType, fullFunction);

            // Process parameter list
            if (!parameterList.trim().equals("void")) {
                String[] parameters = parameterList.split(",");
                for (String param : parameters) {
                    param = param.trim().replaceAll("\\s+", " ");
                    String[] parts = param.split(" ");
                    if (parts.length > 1) {
                        String type = String.join(" ", Arrays.asList(parts).subList(0, parts.length - 1));
                        String name = parts[parts.length - 1];
                        functionInfo.addParameter(type, name);
                    }
                }
            }

            // Extract the function body
            /*
            * Extract function body  using regex
            * find local variable declaration using regex
            * store local variable in functionInfo object
            * */

            String bodyRegex = "\\{(.*)\\}";
            Pattern bodyPattern = Pattern.compile(bodyRegex, Pattern.DOTALL);
            Matcher bodyMatcher = bodyPattern.matcher(fullFunction);
            if (bodyMatcher.find()) {
                String functionBody = bodyMatcher.group(1); // Extract the body content

                // Extract local variables
                String localVarRegex = "(const|volatile|static|extern)?\\s*" +
                        "(int|float|double|char|short|long|unsigned|signed|struct\\s+[a-zA-Z_][a-zA-Z0-9_]*)\\s+" +
                        "([*]*[a-zA-Z_][a-zA-Z0-9_]*(\\s*(\\[\\s*\\d*\\s*\\])*)*(\\s*=\s*[^,;]+)?(\\s*,\\s*[*]*[a-zA-Z_][a-zA-Z0-9_]*(\\s*(\\[\\s*\\d*\\s*\\])*)*(\\s*=\s*[^,;]+)?)*)\\s*;";
                Pattern localVarPattern = Pattern.compile(localVarRegex);
                Matcher localVarMatcher = localVarPattern.matcher(functionBody);

                while (localVarMatcher.find()) {
                    String qualifier = localVarMatcher.group(1) != null ? localVarMatcher.group(1).trim() + " " : ""; // Qualifier
                    String type = qualifier + localVarMatcher.group(2); // Full type (including qualifier)
                    String variableList = localVarMatcher.group(3); // List of variables

                    String[] variables = variableList.split("\\s*,\\s*");
                    for (String variable : variables) {
                        String[] parts = variable.split("\\s*=\\s*"); // Split variable and assignment
                        String name = parts[0].trim(); // Variable name
                        String assignedValue = parts.length > 1 ? parts[1].trim() : null;

                        functionInfo.addLocalVariable(type, name, assignedValue);
                    }
                }
            }
            this.functionInfo.put(key, functionInfo);
        }
    }


    public void mask(){
        MaskedFunction maskedFunction = new MaskedFunction(2);
        functionInfo.forEach((key, value) -> {
            maskedFunction.computeParameterList(value, key);
            maskedFunction.computeLocalVariable(value, key);
        });
        System.out.println("---PRINTING THE MASKED FUNCTION PARAMETER LIST------\n" + maskedFunction.getFunctionInfoHashMap());

    }

    public static void main(String[] args) throws IOException{
        ReadUnmaaskedFile readUnmaaskedFile = new ReadUnmaaskedFile();
        readUnmaaskedFile.extractFunctionsWithBodies("C:\\Users\\nupur\\Desktop\\MTP_iit\\unmasked.cpp");

        System.out.println("printing all the functions in a file");

        readUnmaaskedFile.printAllFunctions();

        System.out.println("Count = "+ ReadUnmaaskedFile.getFunctionsCount());

        readUnmaaskedFile.mask();

        return;
    }


}
