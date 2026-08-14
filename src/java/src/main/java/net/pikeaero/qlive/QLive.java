package net.pikeaero.qlive;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * QLive — Decentralized live streaming for the Qortal network.
 *
 * Java components: Qortal Core integration, cryptographic signing, peer swarm management.
 */
public final class QLive {

    private static final Logger LOGGER = LoggerFactory.getLogger(QLive.class);

    public static final String VERSION = "0.1.0";

    private QLive() {
        // Utility class
    }

    public static void main(String[] args) {
        LOGGER.info("QLive {} — live streaming that belongs to the network, not the platform.", VERSION);
    }
}