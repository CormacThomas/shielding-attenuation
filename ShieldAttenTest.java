/**
 * @(#)ShieldAttenTest.java
 *
 *
 * @author
 * @version 1.00 2025/10/23
 */

import java.util.*;
public class ShieldAttenTest {

    public static void main(String [] args) {
    //simulated gamma energy in MeV
    	double E = .6617;
    //simulated thickness of material in cm
    	double thickness = 1;
    //Photon energy values in MeV
    	double[] energy = {0.001, 0.0015, 0.002, 0.00248, 0.002484, 0.00253, 0.002586, 0.002586,
    0.003, 0.003066, 0.003066, 0.003301, 0.003554, 0.003554, 0.003699, 0.003851,
    0.003851, 0.004, 0.005, 0.006, 0.008, 0.01, 0.01304, 0.015, 0.0152, 0.0152,
    0.01553, 0.01586, 0.01586, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.088, 0.088,
    0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.022, 1.25, 1.5, 2.0, 2.044,
    3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0};
    //mu/P value for lead corresponding to list of energies
    	double[] muOverP = {5209.0, 2356.0, 1285.0, 800.9, 1396.0, 1647.0, 1944.0, 2450.0,
    1965.0, 1857.0, 2146.0, 1792.0, 1496.0, 1585.0, 1441.0, 1302.0,
    1368.0, 1251.0, 730.5, 467.2, 228.7, 130.6, 67.0, 162.1, 111.6, 107.8,
    148.5, 141.2, 134.4, 154.8, 86.37, 30.32, 14.36, 8.056, 5.020, 2.419,
    1.910, 7.684, 5.549, 2.015, 0.4032, 0.2323, 0.1613, 0.125, 0.0887, 0.07102,
    0.06962, 0.05875, 0.05222, 0.04607, 0.04577, 0.04234, 0.0420, 0.04272, 0.04391,
    0.04528, 0.04675, 0.04823, 0.04972};
	//density of the shielding material for linear attenuation coefficient calculation
    	double density = 11.34;
    // linear attenuation coefficient calucation
    	double mu = getMu(E, energy, muOverP, density);
    	System.out.println("Linear attenuation coefficient mu = "+mu+"cm^-1");
    // percentage of photons that pass through the shielding material
    	double transmission = calcTransmission(mu, thickness);
    	System.out.printf("Transmission (percent): %.8f%%\n", transmission*100);


    }
	// log log interpolation to estimate the linear attenuation coefficient for values that do not exist in the NIST list of values
    public static double getMu(double E, double[] energy, double[] muOverP, double density){
    	int i = bracketIndex(E, energy);
    	if(i==-1){
    		System.out.println("Energy out of bounds");
    		return -1;
    	}
    	double E1 = energy[i];
    	double E2 = energy[i+1];
    	double m1 = muOverP[i];
    	double m2 = muOverP[i+1];
    	double lnE1 = Math.log(E1);
    	double lnE2 = Math.log(E2);
    	double lnE = Math.log(E);
    	double lnM1 = Math.log(m1);
    	double lnM2 = Math.log(m2);
	// log log interpolation based on linear interpolation formula
    	double lnM = lnM1+((lnE-lnE1)/(lnE2-lnE1))*(lnM2-lnM1);
    	double m = Math.exp(lnM);
    // interpolation gives mu/density. multiply by density to get mu
    	double mu = m*density;
    	return mu;
    }
	// finds the values that are on either side of the input energy
    public static int bracketIndex(double E, double[] energy){
    	for(int i=0; i<energy.length-1; i++){
    		if(E>=energy[i]&&E<=energy[i+1]){
    			return i;
    		}
    	}
    	return -1;
    }
    // beer-lambert law to calculate for percentage of photon transmission
    public static double calcTransmission(double mu, double thickness){
		return Math.exp(-mu*thickness);
    }


}