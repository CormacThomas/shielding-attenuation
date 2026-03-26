import java.util.*;

/**
 * ShieldingCalculator.java
 *
 * Contains methods to calculate photon attenuation and flux through a stack of shielding layers.
 * Uses Beer-Lambert law for attenuation and the inverse-square law for geometric spreading.
 */
public class ShieldingCalculator{

    //Computes total transmission of photons through multiple layers of shielding.
    public static double computeTransmission(double energy, ArrayList<Layer> layers){
        //Calculations: multiply transmission through each layer (Beer-Lambert)

        //Start with 100% transmission
        double transmission = 1;
        for(Layer layer: layers){
            //Get linear attenuation coefficient mu (1/cm) from Physics class
            double mu = Physics.getMu(energy,layer.material);
            if(mu < 0){
                throw new IllegalStateException("Negative mu encountered.");
            }
            transmission *= Math.exp(-mu*layer.thickness);

            //Optional half-value layer calculation for validation
            //double hvl = Math.log(2)/mu;
            //System.out.println("This is the hvl "+hvl);
        }
        return transmission;
    }
    //Computes photon flux at a given distance from a point source after attenuation.
    //Uses inverse-square law.
    public static double computeFlux(double transmission, double distance,double sourceStrength){
        return sourceStrength * transmission / (4* Math.PI * distance*distance);
    }

}