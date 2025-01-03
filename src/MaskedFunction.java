import java.util.HashMap;

/**
 * class to convert the unmasked function to masked function
 */

public class MaskedFunction {

    int d; // dthI order of security




    HashMap<Integer, FunctionInfo> functionInfoHashMap;

    public MaskedFunction(int d) {
        this.d = d;
        functionInfoHashMap = new HashMap<>();
    }

    public HashMap<Integer, FunctionInfo> getFunctionInfoHashMap() {
        return functionInfoHashMap;
    }

    public FunctionInfo getValue(int key){
        return functionInfoHashMap.get(key);
    }
    /**
     * function to compute the parameter list for masked function
     * rule to create parameter list of masked function.
     *  1. d+1 random variable will be added as the parameter.
     *  2. all the parameter of unmasked function wll be divided into d+1 shares and added to the parameter list.
     *  3. if the function return output then pointer variables will be used for the output d+1 output pointer variables will be added to the parameter list.
     *  input FunctionInfo object
     *  output transformed functions parameter list
     */
    public void computeParameterList(FunctionInfo unmaskedFunction, int id){
        unmaskedFunction.getParameters().forEach((key, value) -> {
                    value.forEach(par-> {

                        FunctionInfo m = functionInfoHashMap.computeIfAbsent(id, x -> new FunctionInfo(unmaskedFunction.getFunctionName()));
                        // par  = a (string)
                        Integer t = (Integer) 0;
                        while(t < d){

                            m.addParameter(key,par+t.toString());
                            functionInfoHashMap.put(id, m);
                            t++;
                        }

                    } );

                }
        );
        FunctionInfo m = functionInfoHashMap.computeIfAbsent(id, x-> new FunctionInfo(unmaskedFunction.getFunctionName()));
        Integer t = (Integer) 0;
        while(t <= d){

            m.addParameter("int","r"+t.toString());
            functionInfoHashMap.put(id, m);
            t++;
        }

    }

    /**
     * include all the declaration and declaration + initialisation into the local varaible list
     * function only adds.
     * valid initialisation in c are
     *      int a, b;
     *      int a;
     *      int b;
     *      int a = 9, b;
     *      int a[];
     *      int *a;
     *      int *a , b;
     *      const int a;
     *      static int a;
     * @param unmaskedFunction
     * @param id
     */
    public void computeLocalVariable(FunctionInfo unmaskedFunction, int id){

        unmaskedFunction.getLocalVariables().forEach((key, value) -> {
                    value.forEach((k, val)-> {

                        FunctionInfo m = functionInfoHashMap.computeIfAbsent(id, x -> new FunctionInfo(unmaskedFunction.getFunctionName()));
                        // par  = a (string)
                        Integer t = (Integer) 0;
                        while(t < d){

                            m.addLocalVariable(key,k+t.toString(), val);
                            functionInfoHashMap.put(id, m);
                            t++;
                        }

                    } );

                }
        );


    }


    /**
     * convert each computation to a 3 address code
     * new local variables created in this process will be added to the local variable list
     *
     * @param unmasked
     */
    public void ConvertTo3AddressCode(FunctionInfo unmasked){

    }

    public void processNonLinearOperation(){

    }



    @Override
    public String toString() {
        return "MaskedFunction{" +
                "d=" + d +
                ", maskedFunctions=" + functionInfoHashMap +
                '}';
    }



    public void transform(){

    }
}
