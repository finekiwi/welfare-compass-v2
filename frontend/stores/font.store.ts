import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FontState {
    size: number; // Percentage (default 100)
    increase: () => void;
    decrease: () => void;
    reset: () => void;
}

export const useFontStore = create<FontState>()(
    persist(
        (set) => ({
            size: 100,
            increase: () => set((state) => ({ size: Math.min(state.size + 10, 150) })), // Max 150%
            decrease: () => set((state) => ({ size: Math.max(state.size - 10, 80) })),  // Min 80%
            reset: () => set({ size: 100 }),
        }),
        {
            name: "font-storage",
        }
    )
);
