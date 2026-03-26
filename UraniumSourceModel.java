import java.util.*;

/**
 * UraniumSourceModel.java
 *
 * Models photon emission from Depleted Uranium (DU) slab.
 * Calculates activity, gamma emission lines, and photon output through material.
 *
 * Assumes secular equilibrium up to Pa-234m
 */
public class UraniumSourceModel{
    //Analyzes photon emission from a DU slab of given thickness and material.
    public static void analyzeDU(double thickness, Material mat){

        //U-238 half-life in seconds
        double tHalf = 4.468e9 * 365.25 * 24 * 3600;

        //Decay constant
        double lambda = Math.log(2)/tHalf;

        //Atoms per gram of U-238
        double atomsPerGram = (6.022e23/238);

        //Activity per gram (Bq/g)
        double A = atomsPerGram * lambda;
        //Activity per volume (Bq/cm^3)
        double Avol = A * 19;

        //Gamma emission lines for U-238 (energy in kev, intensity fraction)
        double [][] lines={{63.28, 0.041},
                {92.37, 0.0242},
                {92.79, 0.0239},
                {112.81, 0.0024},
                {258.19, 0.000754},
                {742.81, 0.00096},
                {766.37, 0.00316},
                {1001.0, 0.00839}};

        //Compute source strength for each gamma line
        for(double[] line: lines){
            double E_keV = line[0];
            double Ig = line[1];
            double Svol = Avol*Ig;

            // System.out.printf("%.2f\t\t%.5f\t%.3e\n", E_keV, Ig, Svol);
        }

        //Compute photon output through material
        for(double[] line: lines){
            double E_keV = line[0];
            double E_MeV = E_keV/1000;
            double Ig = line[1];

            double Svol = Avol*Ig;
            double mu = Physics.getMu(E_MeV, mat);
            double Rout = Svol*(1-Math.exp(-mu*thickness))/mu;
           }

        //Note: These values assume secular equilibrium up to Pa-234m.
    }
}