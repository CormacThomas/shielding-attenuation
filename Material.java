import java.util.*;

/**
 * Material.java
 *
 * Represents a shielding material with attenuation properties.
 *
 * Each material can have:
 * - Name and Density
 * - Energy dependent mass attenuation coefficients (mu/p)
 *   - Optionally, materials can also have
 *     photoelectric, compton scattering, and pair production components.
 */
public class Material{
    //Material name
    String name;
    //Material density in g/cm^3
    double density;
    //Material energies corresponding to attenuation data (MeV)
    double[] energy;
    //Total mass attenuation coefficients (cm^2/g)
    double[] muOverP;
    //Optional components arrays
    double[] muPhotoOverP;
    double[] muComptonOverP;
    double[] muPairOverP;

    //Constructor for materials will full component data
    public Material(String name, double density, double[] energy, double[] muPhotoOverP, double[] muComptonOverP, double[] muPairOverP){
        this.name = name;
        this.density = density;
        this.energy = energy;
        this.muPhotoOverP = muPhotoOverP;
        this.muComptonOverP = muComptonOverP;
        this.muPairOverP = muPairOverP;
    }

    //Constructor for materials with only total mass attenuation
    public Material(String name, double density,
                    double[] energy,
                    double[] muOverP){

        this.name = name;
        this.density = density;
        this.energy = energy;

        this.muOverP = muOverP;

        // component arrays remain null
        this.muPhotoOverP = null;
        this.muComptonOverP = null;
        this.muPairOverP = null;
    }
}