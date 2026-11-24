/**
 * @(#)ShieldAttenuationMain.java
 *
 * Entry point for the photon shielding attenuation simulator.
 *
 * This program models photon flux at a detector by accounting for
 * material attenuation using the Beer-Lambert Law and Geometric spreading
 * using the inverse-square law.
 *
 * @version 1.01
 */

import java.util.*;
public class ShieldAttenuationMain {

	public static void main(String [] args) {

		//Photon energy in MeV (Cs-137 reference)
		double E = .6617;

		//Source strength in photons/s roughly equivalent to 1 Ci
		double S = 3.7e10;

		//Read shielding configuration
		Scanner scan = new Scanner(System.in);

		//Read shielding config(multi-layer)
		ArrayList<Layer> layers = InputHandler.readLayers(scan);

		//Read detector distance from source
		double distance = InputHandler.readDistance(scan);

		//Compute shielding transmission and flux
		double transmission = ShieldingCalculator.computeTransmission(E,layers);
		double flux = ShieldingCalculator.computeFlux(transmission,distance,S);

		//Output results
		OutputHandler.printResults(layers,distance,transmission, flux);

		//Special case: not fully implemented. Depleted Uranium.
		boolean hasDU = false;
		Layer duLayer = null;

		//Check whether any layer contains DU
		for(Layer layer :layers){
			if(layer.material.name.equals("Depleted Uranium (DU)")){
				hasDU = true;
				duLayer = layer;
			}
		}
		//If DU is present, perform source modeling
		if(hasDU){
			UraniumSourceModel.analyzeDU(duLayer.thickness,duLayer.material);
		}
		scan.close();
	}
}
