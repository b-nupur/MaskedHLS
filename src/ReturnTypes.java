public enum ReturnTypes {
    VOID("void"),
    INT("int"),
    FLOAT("float"),
    DOUBLE("double"),
    CHAR("char"),
    POINTER("pointer"),
    STRUCT("struct"),
    ENUM("enum"),
    UNION("union");

    private String returnType;

    private ReturnTypes(String val){
        this.returnType = val;
    }

    public String getReturnType() {
        return returnType;
    }
}
