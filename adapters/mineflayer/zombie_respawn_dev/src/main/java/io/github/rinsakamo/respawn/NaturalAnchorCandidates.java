package io.github.rinsakamo.respawn;

import java.util.ArrayList;
import java.util.List;

/**
 * Search only existing terrain near Self for a valid managed-zombie anchor.
 * No blocks, player position, mob AI or physics are modified. A candidate
 * is only a proposal: the Paper plugin must still verify the actual blocks.
 */
final class NaturalAnchorCandidates {
    private NaturalAnchorCandidates() {}

    static List<int[]> offsets() {
        // Prefer the historical x+6 test anchor, then other nearby sites.
        // No zero-distance proposal and no arbitrary remote relocation.
        int[][] horizontal = {
            {6, 0}, {-6, 0}, {0, 6}, {0, -6},
            {6, 3}, {6, -3}, {-6, 3}, {-6, -3},
            {3, 6}, {-3, 6}, {3, -6}, {-3, -6},
            {4, 0}, {-4, 0}, {0, 4}, {0, -4},
        };
        List<int[]> proposals = new ArrayList<>();
        for (int[] site : horizontal) {
            proposals.add(new int[] {site[0], 0, site[1]});
            for (int dy = 1; dy <= 8; dy++) {
                proposals.add(new int[] {site[0], dy, site[1]});
                proposals.add(new int[] {site[0], -dy, site[1]});
            }
        }
        return List.copyOf(proposals);
    }
}
