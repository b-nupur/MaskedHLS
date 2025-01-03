
import java.util.*;

public class FunctionInfo {
    private String functionName;
    private String returnType;
    private String functionBody;
//    private Integer functionId;
    // private HashSet<Variable> parameters;
    private Map<String, HashSet<String>> parameters; // Map of type to parameter names
    // private HashSet<Variable> localVariable;
    private Map<String, Map<String, String>> localVariables; // Type -> Map of Variable Name -> Assigned Value

    public FunctionInfo(String functionName, String returnType, String functionBody) {
        this.functionName = functionName;
        this.returnType = returnType;
        this.functionBody = functionBody;
        this.parameters = new HashMap<>();
        this.localVariables = new HashMap<>();
    }

    public FunctionInfo(String name){
        this.functionName = name;
        this.parameters = new HashMap<>();
        this.localVariables = new HashMap<>();
    }

    public FunctionInfo(String functionName, String returnType) {
        this.functionName = functionName;
        this.returnType = returnType;
        this.parameters = new HashMap<>();
        this.localVariables = new HashMap<>();
    }

    public String getFunctionBody() {
        return functionBody;
    }

    public void setFunctionBody(String functionBody) {
        this.functionBody = functionBody;
    }
    public void addParameter(String type, String name) {
        // Check if the type already exists
        parameters.computeIfAbsent(type, k -> new HashSet<>()).add(name);
    }

//    public void addLocalVariable(String name, String type, String value) {
//        localVariables.add(new Variable(name, type, value));
//    }
    // assuming the
    public void addLocalVariable(String type, String name, String assignedValue) {
        localVariables.computeIfAbsent(type, k -> new HashMap<>()).put(name, assignedValue);
    }


    public String getFunctionName() {
        return functionName;
    }

    public String getReturnType() {
        return returnType;
    }

    public Map<String, HashSet<String>> getParameters() {
        return parameters;
    }

    public Map<String, Map<String, String>> getLocalVariables() {
        return localVariables;
    }

//    public HashSet<Variable> getLocalVariables() {
//        return localVariables;
//    }


    public void printFunctionInfo() {
        System.out.println("\nPrinting function info ...\n");
        System.out.println(functionBody);
        System.out.println("Function Name: " + functionName);
        System.out.println("Return Type: " + returnType);
        System.out.println("Parameters: "+ parameters.size());
        for (Map.Entry<String, HashSet<String>> entry : parameters.entrySet()) {
            System.out.println("  " + entry.getKey() + ": " + entry.getValue());
        }
        System.out.println("Local Variables: " +localVariables );

        System.out.println("---------------------------------------------");
    }

    @Override
    public String toString() {
        return "FunctionInfo{" +
                "functionName=" + functionName + "\n" +
                "returnType=" + returnType + "\n" +
                "functionBody=" + functionBody + "\n" +
                "parameters=" + parameters + "\n" +
                "localVariables=" + localVariables + "\n" +
                "}\n";
    }
}

