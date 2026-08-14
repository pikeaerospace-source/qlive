# QLive Java Components

Java components for the QLive decentralized live-streaming protocol.

## Planned Components

| Component | Status | Description |
| --- | --- | --- |
| `qortal-core/` | Planned | Qortal Core integration (QDN signaling, identity) |
| `signing/` | Planned | Cryptographic chunk signing/verification |
| `swarm/` | Planned | Peer swarm management |

## Development

```bash
# Build
mvn clean package

# Test
mvn test

# Run
mvn exec:java
```

## Dependencies

- Java 17+
- Maven 3.8+
- See `pom.xml` for full dependency list