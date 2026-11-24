/**
 * Physics.java
 *
 * Contains physics utility methods for photon attenuation calculations.
 *
 * Calculates linear attenuation coefficients (mu) for a material at a given photon energy.
 * Uses log-log interpolation for non-tabulated energies.
 */
public class Physics{

    /*Estimes the linear attenuation coefficient (mu) (1/cm) for a material at photon energy E.
      Uses NIST mass attenuation tables for photoelectric, Compton, and pair production contributions.
    */
    public static double getMu(double E, Material mat){
        if(mat.muPhotoOverP !=null && mat.muComptonOverP!=null&&mat.muPairOverP!=null){
            //Interpolate each contribution separately
            double photo = interpolate(E, mat.energy, mat.muPhotoOverP);
            double compton = interpolate(E, mat.energy, mat.muComptonOverP);
            double pair = interpolate(E, mat.energy, mat.muPairOverP);

            double muOverP = photo + compton + pair;
            //Convert mass attenuation (1/cm^2/g) to linear attenuation (1/cm)
            return muOverP * mat.density;
        }
        if(mat.muOverP !=null){
            double muOverP = interpolate(E, mat.energy, mat.muOverP);
            return muOverP *mat.density;
        }
        throw new IllegalStateException("Material has no attenuation data.");
    }
    //Performs log-log interpolation between tabulated values. Falls back to linear interpolation if values are negative or zero.
    public static double interpolate(double E, double[] energy, double[] values){
        int i = bracketIndex(E, energy);

        if(i==-1){
            throw new IllegalArgumentException("Energy " + E + " MeV out of bounds ["
                    + energy[0] + ", " + energy[energy.length-1] + "]");
        }
        double E1 = energy[i];
        double E2 = energy[i+1];
        double V1 = values[i];
        double V2 = values[i+1];

        //Linear attenuation if one of the values is zero or negative
        if(V1 <= 0 || V2 <= 0){
            return V1 + ((E - E1)/(E2 - E1))*(V2 - V1);
        }
        double lnE = Math.log(E);
        double lnE1 = Math.log(E1);
        double lnE2 = Math.log(E2);
        double lnV1 = Math.log(V1);
        double lnV2 = Math.log(V2);

        double lnV = lnV1 + ((lnE - lnE1)/(lnE2 - lnE1))*(lnV2 - lnV1);

        return Math.exp(lnV);
    }

    //Finds the index "i" such that E lies between energy[i] and energy[i+1]
    //Returns -1 if E is outside the range
    public static int bracketIndex(double E, double[] energy){
        for (int i = 0; i < energy.length - 1; i++) {
            if (energy[i] == energy[i + 1]) continue; //Skip duplicates
            if (E >= energy[i] && E <= energy[i + 1]) return i;
        }
        return -1;
    }
}