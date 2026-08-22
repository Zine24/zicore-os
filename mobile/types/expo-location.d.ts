declare module 'expo-location' {
  export type LocationPermissionStatus = 'granted' | 'denied' | 'undetermined';

  export interface LocationCoords {
    latitude: number;
    longitude: number;
    accuracy?: number | null;
    altitude?: number | null;
    speed?: number | null;
    heading?: number | null;
  }

  export interface LocationObject {
    coords: LocationCoords;
    timestamp: number;
  }

  export const Accuracy: {
    Lowest: number;
    Low: number;
    Balanced: number;
    High: number;
    Highest: number;
  };

  export function requestForegroundPermissionsAsync(): Promise<{ status: LocationPermissionStatus }>;
  export function requestBackgroundPermissionsAsync(): Promise<{ status: LocationPermissionStatus }>;
  export function getCurrentPositionAsync(options?: {
    accuracy?: number;
    timeout?: number;
    maximumAge?: number;
  }): Promise<LocationObject>;
  export function getLastKnownPositionAsync(options?: {
    maxAge?: number;
    requiredAccuracy?: number;
  }): Promise<LocationObject | null>;
  export function watchPositionAsync(
    options: { accuracy?: number; timeInterval?: number; distanceInterval?: number },
    callback: (location: LocationObject) => void
  ): Promise<{ remove: () => void }>;
}
