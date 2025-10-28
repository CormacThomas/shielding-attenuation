/**
 * @(#)ShieldAttenTest.java
 *
 * Simulates photon attenuation through shielding material,
 * accounting for shielding attenuation coefficient (Beer-Lambert Law)
 * and geometric spreading (Inverse-Square Law).
 *
 * @author
 * @version 1.01
 */

import java.util.*;
public class ShieldAttenTest {

    public static void main(String [] args) {

    	//Constants and setup
    	//Simulated photon energy (MeV) - will be replaced with user input
    	double E = .6617; //Example Cs-137 photon energy
    	Scanner scan = new Scanner(System.in);

    	//User input section
   		System.out.println("Enter material name (lead, concrete, water): ");
   		String choice = scan.nextLine().toLowerCase();

   		System.out.println("Enter shielding thickness (cm): ");
   		double thickness = scan.nextDouble();

   		System.out.println("Enter distance from source to detector (cm): ");
   		double distance = scan.nextDouble();

   		//Geometric possibility check
   		//Detector must not be located beyond or in the shield.
		if(distance <= thickness){
			System.out.println("Error: Distance must be greater than shielding thickness.");
			System.out.println("Detector must be located beyond the shield.");
			return;
		}

		//Material selection
   		Material mat = null;

    	if (choice.equals("lead")){
    		mat= createLead();
    	}else if(choice.equals("concrete")){
  			//mat= createConcrete();
   		}else if(choice.equals("water")){
    		//mat= createWater();
    	}else{
    		System.out.println("Material not found.");
    		return;
   		}

		//Linear attenuation coefficient (mu) calculation
        //Uses log-log interpolation to find u/p at the input energy,
        //then multiplies by density to get mu (cm^-1)
    	double mu = Physics.getMu(E, mat);

    	System.out.println("\nMaterial: "+mat.name);
    	System.out.println("Linear attenuation coefficient for  mu = "+mu+"cm^-1");

   		//Transmission calculation
        //Combines exponential attenuation and inverse-square law
    	double transmission = Physics.calcTransmission(mu, thickness, distance);

    	System.out.printf("Transmission through %.2f cm thickness: at %.2f cm distance): %.8f%%\n",thickness, distance, transmission*100);


    }


	//Defines lead attenuation data from NIST XCOM.
    //Returns a Material object containing energy and u/p values.
    public static Material createLead(){
    	double[] energy = {0.001, 0.0015, 0.002, 0.00248, 0.002484, 0.00253, 0.002586, 0.002586,
    		0.003, 0.003066, 0.003066, 0.003301, 0.003554, 0.003554, 0.003699, 0.003851,
    		0.003851, 0.004, 0.005, 0.006, 0.008, 0.01, 0.01304, 0.015, 0.0152, 0.0152,
    		0.01553, 0.01586, 0.01586, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.088, 0.088,
    		0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.022, 1.25, 1.5, 2.0, 2.044,
   			3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0};
    	double[] muOverP = {5209.0, 2356.0, 1285.0, 800.9, 1396.0, 1647.0, 1944.0, 2450.0,
    		1965.0, 1857.0, 2146.0, 1792.0, 1496.0, 1585.0, 1441.0, 1302.0,
    		1368.0, 1251.0, 730.5, 467.2, 228.7, 130.6, 67.0, 162.1, 111.6, 107.8,
    		148.5, 141.2, 134.4, 154.8, 86.37, 30.32, 14.36, 8.056, 5.020, 2.419,
    		1.910, 7.684, 5.549, 2.015, 0.4032, 0.2323, 0.1613, 0.125, 0.0887, 0.07102,
    		0.06962, 0.05875, 0.05222, 0.04607, 0.04577, 0.04234, 0.0420, 0.04272, 0.04391,
    		0.04528, 0.04675, 0.04823, 0.04972};
    	return new Material("Lead", 11.34, energy, muOverP);
    }
}

class Material{
	String name;
	double density;
	double[] energy;
	double[] muOverP;

	public Material(String name, double density, double[] energy, double[] muOverP){
		this.name = name;
		this.density = density;
		this.energy = energy;
		this.muOverP = muOverP;
	}
}
//
class Physics{

	//Calculates linear attenuation coefficient mu using log-log interpolation.
    //The NIST tables provide mu/p at specified photon energies, so this method
    //estimates mu at any given energy between known points.
	public static double getMu(double E, Material mat){
		int i = bracketIndex(E, mat.energy);
    	if(i==-1){
    		System.out.println("Energy out of bounds for "+mat.name);
    		return -1;
    	}

    	//Values on either side of the desired photon energy
    	double E1 = mat.energy[i];
    	double E2 = mat.energy[i+1];
    	double m1 = mat.muOverP[i];
    	double m2 = mat.muOverP[i+1];

    	//Log-log interpolation based on linear interpolation formula
    	double lnE1 = Math.log(E1);
    	double lnE2 = Math.log(E2);
    	double lnE = Math.log(E);
    	double lnM1 = Math.log(m1);
    	double lnM2 = Math.log(m2);
    	double lnM = lnM1+((lnE-lnE1)/(lnE2-lnE1))*(lnM2-lnM1);

    	//Convert back from log scale
    	double m = Math.exp(lnM);

   		//Interpolation gives mu/density. Multiply by density to get mu.
    	double mu = m*mat.density;
    	return mu;
	}

	//Finds the index "i" such that E lies between energy[i] and energy[i+1].
    //Returns -1 if E is outside the range.
	public static int bracketIndex(double E, double[] energy){
    	for(int i=0; i<energy.length-1; i++){
    		if(E>=energy[i]&&E<=energy[i+1]){
    			return i;
    		}
    	}
    	return -1;
    }

    //Calculates transmitted fraction of photons through a material and air gap.
    //Beer-Lambert Law
    //Inverse-Square Law
    public static double calcTransmission(double mu, double thickness, double distance){
    	double shieldingFactor = Math.exp(-mu*thickness); //exponential attenuation
    	double distanceFactor = 1.0 / Math.pow(distance, 2); //inverse-square spreading
		return shieldingFactor * distanceFactor;
    }

}