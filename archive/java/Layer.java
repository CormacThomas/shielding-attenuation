/**
 * Layer.java
 *
 * Represents a single shielding layer in the photon attenuation simulation.
 *
 * Each layer has its own material type and thickness in centimeters.
 */
public class Layer{
    //Material assigned to this layer
    Material material;
    //Thickness of the layer in centimeters
    double thickness;

    //Constructor to create the shielding layer
    public Layer(Material material, double thickness){
        this.material = material;
        this.thickness = thickness;
    }
}