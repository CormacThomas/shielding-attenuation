import java.util.*;

/**
 * OutputHandler.java
 *
 * Handles printing of simulation results.
 */
public class OutputHandler{
    public static void printResults(ArrayList<Layer> layers, double distance, double transmission, double flux){
        double totalThickness = 0;
        System.out.println("\nResults");
        //Print each layer's material and thickness
        for(int i = 0; i<layers.size(); i++){
            Layer l = layers.get(i);
            System.out.printf("Layer %d: %s (%.2f cm)\n",i+1,l.material.name,l.thickness);
            totalThickness +=l.thickness;
        }
        //Print total thickness of all materials combined
        System.out.printf("\nTotal thickness: %.2f cm\n",totalThickness);

        //Print shield transmission (dimensionless, converted to %)
        System.out.printf("Shield transmission: %.6f%%\n", transmission*100);

        //Print photon flux at specified distance
        System.out.printf("Flux at %.2f cm: %.8e (photons/cm^2/s)\n",distance,flux);
    }
}