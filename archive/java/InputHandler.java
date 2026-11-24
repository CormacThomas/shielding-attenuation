import java.util.*;

/**
 * InputHandler.java
 *
 * Handles all user input for the shielding attenuation simulator.
 */
public class InputHandler{
    /*
      Reads a list of shielding layers from user input.
      Each layer consists of a selected material and user
      defined thickness in centimeters.
      Returns a list of configured shielding layers.
     */
    public static ArrayList<Layer> readLayers(Scanner scan){

        ArrayList<Layer> layers = new ArrayList<>();

        System.out.print("Enter number of shielding layers: ");
        int numLayers = scan.nextInt();

        //Iterate through each layer and collect data
        for(int i = 1; i<=numLayers; i++){

            //Obtain user material selection
            int choice = readMaterialChoice(scan,i);
            Material mat = MaterialLibrary.getMaterial(choice);

            //Make sure selection exists
            if(mat == null){
                System.out.println("Invalid material choice.");
                i--;
                continue;
            }

            //Obtain user thickness selection in cm
            System.out.println("Enter Shielding Thickness (cm): ");
            double thickness = scan.nextDouble();

            //Store layer configuration
            layers.add(new Layer(mat, thickness));
        }
        return layers;
    }
    //Displays material menu
    public static int readMaterialChoice(Scanner scan,int layer){
        System.out.println("\nSelect material for layer " +layer+":");
        System.out.println("Select a material:");
        System.out.println("1. Lead");
        System.out.println("2. Concrete, Ordinary");
        System.out.println("3. Concrete, Barite");
        System.out.println("4. Aluminum");
        System.out.println("5. Water (liquid)");
        System.out.println("6. Tungsten");
        System.out.println("7. Bismuth");
        System.out.println("8. Copper");
        System.out.println("9. Tin");
        System.out.println("10. Polyethylene");
        System.out.println("11. Graphite");
        System.out.println("12. Leaded Glass");
        System.out.println("13. Depleted Uranium");
        return scan.nextInt();
    }
    //Reads detector from source distance in cm
    public static double readDistance(Scanner scan){

        System.out.print("Enter detector distance (cm): ");
        return scan.nextDouble();
    }
}