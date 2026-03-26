import java.util.*;
public class InputHandler{
    //Read shielding layers from user
    public static ArrayList<Layer> readLayers(Scanner scan){
        ArrayList<Layer> layers = new ArrayList<>();
        System.out.print("Enter number of shielding layers: ");
        int numLayers = scan.nextInt();
        //loop over each layer
        for(int i = 1; i<=numLayers; i++){
            //get material selection
            int choice = readMaterialChoice(scan,i);
            Material mat = MaterialLibrary.getMaterial(choice);
            //make sure selection exists
            if(mat == null){
                System.out.println("Invalid material choice.");
                i--;
                continue;
            }
            //Get thickness in cm
            System.out.println("Enter Shielding Thickness (cm): ");
            double thickness = scan.nextDouble();
            //store layer
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
    //reads detector distance in cm
    public static double readDistance(Scanner scan){
        //distance from point source to surface of detector
        System.out.print("Enter detector distance (cm): ");
        return scan.nextDouble();
    }
}