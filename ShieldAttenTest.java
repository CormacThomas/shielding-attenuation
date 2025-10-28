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
   		System.out.println("Select a material:");
   		System.out.println("1. Lead");
   		System.out.println("2. Concrete, Ordinary");
   		System.out.println("3. Concrete, Barite");
   		System.out.println("4. Aluminum");
   		System.out.println("5. Water (liquid)");
   		System.out.println("6. Tunsten");
   		System.out.println("7. Bismuth");
   		System.out.println("8. Copper");
   		System.out.println("9. Tin");
   		System.out.println("10 Polyethylene");
   		System.out.println("11 Graphite");
   		System.out.println("12 Leaded Glass");
   		int choice = scan.nextInt();
   		Material mat = MaterialLibrary.getMaterial(choice);
   		if(mat == null){
   			System.out.println("Invalid choice.");
   			return;
   		}

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
   		/*Material mat = null;

    	if (choice.equals("lead")){
    		mat= createLead();
    	}else if(choice.equals("concrete")){
  			//mat= createConcrete();
   		}else if(choice.equals("water")){
    		//mat= createWater();
    	}else{
    		System.out.println("Material not found.");
    		return;
   		}*/

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

class MaterialLibrary{

	public static Material getMaterial(int choice){
		if(choice == 1){
			return createLead();
		}else if(choice == 2){
			return createConcreteO();
		}else if(choice == 3){
			return createConcreteB();
		}else if(choice == 4){
			return createAluminum();
		}else if(choice == 5){
			return createWater();
		}else if(choice == 6){
			return createTungsten();
		}else if(choice == 7){
			return createBismuth();
		}else if(choice == 8){
			return createCopper();
		}else if(choice == 9){
			return createTin();
		}else if(choice == 10){
			return createPolyethylene();
		}else if(choice == 11){
			return createGraphite();
		}else if(choice == 12){
			return createLeadedGlass();
		}else{
			return null;
		}
	}
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
	public static Material createConcreteO() {
    	double[] energy = {0.001000, 0.001035, 0.001072, 0.0011828, 0.001305, 0.0015, 0.0015596, 0.0016935,
        	0.0018389, 0.0020, 0.0030, 0.003607, 0.0040, 0.004038, 0.0050, 0.0060, 0.007112,
        	0.0080, 0.0100, 0.0150, 0.0200, 0.0300, 0.0400, 0.0500, 0.0600, 0.0800, 0.1000,
        	0.1500, 0.2000, 0.3000, 0.4000, 0.5000, 0.6000, 0.8000, 1.0000, 1.2500, 1.5000,
        	2.0000, 3.0000, 4.0000, 5.0000, 6.0000, 8.0000, 10.0000};

    	double[] muOverP = {3466, 3164, 2889, 2302, 1775, 1227, 1104, 941.9, 752.5, 1368,
        	464.6, 280.4, 218.8, 213.1, 140.1, 84.01, 51.87, 38.78, 20.45,
        	6.351, 2.806, 0.9601, 0.5058, 0.3412, 0.2660, 0.2014, 0.1738,
        	0.1436, 0.1282, 0.1097, 0.09783, 0.08915, 0.08236, 0.07227, 0.06495,
        	0.05807, 0.05288, 0.04557, 0.03701, 0.03217, 0.02908, 0.02697, 0.02432, 0.02278};

   			double density = 2.4;

    	return new Material("Concrete (Ordinary)", density, energy, muOverP);
	}
	public static Material createConcreteB() {
	    double[] energy = {0.001000, 0.001031, 0.001062, 0.0010988, 0.0011367, 0.001212, 0.001293,
	        0.001299, 0.001305, 0.001500, 0.0015596, 0.0016935, 0.0018389, 0.002000,
	        0.002472, 0.003000, 0.004000, 0.004038, 0.005000, 0.005247, 0.005432,
	        0.005623, 0.005803, 0.005989, 0.006000, 0.007112, 0.008000, 0.010000,
	        0.015000, 0.020000, 0.030000, 0.03744, 0.040000, 0.050000, 0.060000,
	        0.080000, 0.100000, 0.150000, 0.200000, 0.300000, 0.400000, 0.500000,
	        0.600000, 0.800000, 1.000000, 1.250000, 1.500000, 2.000000, 3.000000,
	        4.000000, 5.000000, 6.000000, 8.000000, 10.000000};

	    double[] muOverP = {6349, 5916, 5507, 5563, 5150, 4632, 4001, 4082, 4038, 2917, 2659,
	        2195, 1798, 1491, 879.5, 669.2, 319.0, 311.3, 204.8, 180.5, 335.2,
	        306.9, 363.3, 335.3, 376.0, 243.7, 192.5, 106.7, 36.01, 16.55, 5.551,
	        3.091, 11.85, 6.671, 4.143, 1.968, 1.122, 0.4423, 0.2568, 0.1460,
	        0.1104, 0.09309, 0.08245, 0.06936, 0.06112, 0.05404, 0.04915, 0.04296,
	        0.03676, 0.03388, 0.03240, 0.03162, 0.03116, 0.03138};
	    double density = 3.5;

	    return new Material("Concrete (Barite, Type BA)", density, energy, muOverP);
	}

	public static Material createAluminum() {
	    double[] energy = {0.001000, 0.001500, 0.0015596, 0.002000, 0.003000, 0.004000, 0.005000, 0.006000,
	        0.008000, 0.010000, 0.015000, 0.020000, 0.030000, 0.040000, 0.050000, 0.060000,
	        0.080000, 0.100000, 0.150000, 0.200000, 0.300000, 0.400000, 0.500000, 0.600000,
	        0.800000, 1.000000, 1.250000, 1.500000, 2.000000, 3.000000, 4.000000, 5.000000,
	        6.000000, 8.000000, 10.000000};

	    double[] muOverP = {1185, 402.2, 362.1, 2263, 788.0, 360.5, 193.4, 115.3, 50.33, 26.23,
	        7.955, 3.441, 1.128, 0.5685, 0.3681, 0.2778, 0.2018, 0.1704, 0.1378, 0.1223,
	        0.1042, 0.09276, 0.08445, 0.07802, 0.06841, 0.06146, 0.05496, 0.05006,
	        0.04324, 0.03541, 0.03106, 0.02836, 0.02655, 0.02437, 0.02318};

	    double density = 2.7;

	    return new Material("Aluminum", density, energy, muOverP);
	}

	public static Material createWater() {
	    double[] energy = {0.001000, 0.001500, 0.002000, 0.003000, 0.004000, 0.005000, 0.006000, 0.008000,
	        0.010000, 0.015000, 0.020000, 0.030000, 0.040000, 0.050000, 0.060000, 0.080000,
	        0.100000, 0.150000, 0.200000, 0.300000, 0.400000, 0.500000, 0.600000, 0.800000,
	        1.000000, 1.250000, 1.500000, 2.000000, 3.000000, 4.000000, 5.000000, 6.000000,
	        8.000000, 10.000000};

	    double[] muOverP = {4078, 1376, 617.3, 192.9, 82.78, 42.58, 24.64, 10.37, 5.329, 1.673,
	        0.8096, 0.3756, 0.2683, 0.2269, 0.2059, 0.1837, 0.1707, 0.1505, 0.1370, 0.1186,
	        0.1061, 0.09687, 0.08956, 0.07865, 0.07072, 0.06323, 0.05754, 0.04942, 0.03969,
	        0.03403, 0.03031, 0.02770, 0.02429, 0.02219};

	    double density = 1.0;

	    return new Material("Water (Liquid)", density, energy, muOverP);
	}

	public static Material createTungsten() {
	    double[] energy = {0.001000, 0.001500, 0.001809, 0.001840, 0.001872, 0.002000, 0.002281, 0.002424, 0.002575,
	        0.002694, 0.002820, 0.003000, 0.004000, 0.005000, 0.006000, 0.008000, 0.010000, 0.010207,
	        0.010855, 0.011544, 0.011819, 0.012100, 0.015000, 0.020000, 0.030000, 0.040000, 0.050000,
	        0.060000, 0.069525, 0.080000, 0.100000, 0.150000, 0.200000, 0.300000, 0.400000, 0.500000,
	        0.600000, 0.800000, 1.000000, 1.250000, 1.500000, 2.000000, 3.000000, 4.000000, 5.000000,
	        6.000000, 8.000000, 10.000000};

	    double[] muOverP = {3683, 1643, 1108, 1911, 2901, 3922, 2828, 2833, 2445, 2339, 2104, 1902,
	        956.4, 553.4, 351.4, 170.5, 96.91, 92.01, 198.3, 168.9, 226.8, 206.5,
	        138.9, 65.73, 22.73, 10.67, 5.949, 3.713, 2.552, 7.810, 4.438, 1.581,
	        0.7844, 0.3238, 0.1925, 0.1378, 0.1093, 0.08066, 0.06618, 0.05577, 0.05000,
	        0.04433, 0.04075, 0.04038, 0.04103, 0.04210, 0.04472, 0.04747};

	    double density = 19.254;

	    return new Material("Tungsten", density, energy, muOverP);
	}

	public static Material createBismuth() {
	    double[] energy = {0.001000, 0.001500, 0.002000, 0.002580, 0.002633, 0.002688, 0.003000, 0.003177, 0.003427,
	        0.003696, 0.003845, 0.003999, 0.004000, 0.005000, 0.006000, 0.008000, 0.010000, 0.013419,
	        0.015000, 0.015711, 0.016046, 0.016388, 0.020000, 0.030000, 0.040000, 0.050000, 0.060000,
	        0.080000, 0.100000, 0.150000, 0.200000, 0.300000, 0.400000, 0.500000, 0.600000, 0.800000,
	        1.000000, 1.250000, 1.500000, 2.000000, 3.000000, 4.000000, 5.000000, 6.000000, 8.000000,
	        10.000000};

	    double[] muOverP = {5441, 2468, 1348, 772.4, 1850, 1852, 2053, 1774, 1707, 1415, 1366, 1243, 1296,
	        758.0, 485.5, 237.8, 136.0, 64.91, 116.0, 102.7, 135.1, 128.2, 77.24, 26.78,
	        12.58, 7.270, 4.953, 2.869, 1.865, 0.961, 0.573, 0.320, 0.224, 0.171, 0.140,
	        0.119, 0.101, 0.089, 0.080, 0.066, 0.048, 0.038, 0.032, 0.028, 0.025};

	    double density = 9.78;

	    return new Material("Bismuth", density, energy, muOverP);
	}
	public static Material createCopper(){
	    double[] energy = {0.001000, 0.00104695, 0.00109610, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008,
	        0.0089789, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1,
	        0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5,
	        2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0};
	    double[] muOverP = {10570, 9307, 8242, 4418, 2154, 748.8, 347.3, 189.9, 115.6, 52.55,
	        278.4, 215.9, 74.05, 33.79, 10.92, 4.862, 2.613, 1.593, 0.763, 0.4584,
	        0.2217, 0.1559, 0.1119, 0.09413, 0.08362, 0.07625, 0.06605, 0.05901, 0.05261, 0.04803,
	        0.04205, 0.03599, 0.03318, 0.03177, 0.03108, 0.03074, 0.03103};
	    return new Material("Copper", 8.96, energy, muOverP);
	}

	public static Material createTin(){
	    double[] energy = {0.001, 0.0015, 0.002, 0.003, 0.0039288, 0.004, 0.0041561, 0.0043076, 0.0044647, 0.005,
	        0.006, 0.008, 0.01, 0.015, 0.02, 0.0292001, 0.03, 0.04, 0.05, 0.06,
	        0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0,
	        1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0};
	    double[] muOverP = {8157, 3296, 1665, 614.3, 311.4, 939.3, 846.9, 1060, 971.2, 847.1,
	        529.4, 250, 138.4, 46.64, 21.46, 43.6, 41.21, 19.42, 10.7, 6.564,
	        3.029, 1.676, 0.6091, 0.326, 0.1639, 0.1156, 0.09374, 0.08113, 0.06662, 0.058,
	        0.05095, 0.04638, 0.04112, 0.03686, 0.03561, 0.03548, 0.03583, 0.03724, 0.03895};
	    return new Material("Tin", 7.31, energy, muOverP);
	}

	public static Material createPolyethylene(){
	    double[] energy = {0.001, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.01, 0.015,
	        0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3,
	        0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0,
	        5.0, 6.0, 8.0, 10.0};
	    double[] muOverP = {1894, 599.9, 259.3, 77.43, 32.42, 16.43, 9.432, 3.975, 2.088, 0.7452,
	        0.4315, 0.2706, 0.2275, 0.2084, 0.197, 0.1823, 0.1719, 0.1534, 0.1402, 0.1217,
	        0.1089, 0.09947, 0.09198, 0.08078, 0.07262, 0.06495, 0.0591, 0.05064, 0.04045, 0.03444,
	        0.03045, 0.0276, 0.02383, 0.02145};
	    return new Material("Polyethylene", 0.94, energy, muOverP);
	}

	public static Material createGraphite(){
	    double[] energy = {0.001, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.01, 0.015,
	        0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3,
	        0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0,
	        5.0, 6.0, 8.0, 10.0};
	    double[] muOverP = {2211, 700.2, 302.6, 90.33, 37.78, 19.12, 10.95, 4.576, 2.373, 0.8071,
	        0.442, 0.2562, 0.2076, 0.1871, 0.1753, 0.161, 0.1514, 0.1347, 0.1229, 0.1066,
	        0.09546, 0.08715, 0.08058, 0.07076, 0.06361, 0.0569, 0.05179, 0.04442, 0.03562, 0.03047,
	        0.02708, 0.02469, 0.02154, 0.01959};
	    return new Material("Graphite", 2.26, energy, muOverP);
	}

	public static Material createLeadedGlass(){
	    double[] energy = {0.001, 0.00115026, 0.00132310, 0.00134073, 0.00135860, 0.0015, 0.0015265, 0.00167543, 0.0018389, 0.002,
	        0.002484, 0.00253429, 0.0025856, 0.003, 0.0030664, 0.004, 0.005, 0.006, 0.008, 0.01,
	        0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.2,
	        0.3, 0.4, 0.5, 0.6, 0.8, 1.0};
	    double[] muOverP = {4816, 3619, 2704, 2639, 2567, 2088, 2014, 1646, 1339, 1316,
	        802.6, 1488, 1641, 1596, 1390, 644.2, 342.3, 213.8, 106.5, 59.98,
	        20.85, 9.81, 3.51, 1.835, 1.091, 0.7518, 0.4436, 0.2799, 0.1299, 0.07644,
	        0.03799, 0.02209, 0.01527, 0.01172, 0.007963, 0.006061};
	    return new Material("Leaded Glass", 5.05, energy, muOverP);
	}




}