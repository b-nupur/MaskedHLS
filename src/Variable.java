import java.util.Objects;

public class Variable {

    public String getType() {
        return type;
    }

    public String getName() {
        return name;
    }

    public String getValue() {
        return value;
    }

    public Variable(String type, String name, String assignedValue) {
        this.type = type;
        this.name = name;
        this.value = assignedValue;
    }

    String type;
    String name;
    String value;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Variable variable = (Variable) o;
        return name.equals(variable.name) && type.equals(variable.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, type);
    }

    @Override
    public String toString() {
        return name + " (" + type + (value != null ? " = " + value : "") + ")";
    }

}
