import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'zicore_token';
const USER_KEY = 'zicore_user';

export const authStorage = {
  getToken: () => SecureStore.getItemAsync(TOKEN_KEY),

  setToken: (token: string) => SecureStore.setItemAsync(TOKEN_KEY, token),

  removeToken: () => SecureStore.deleteItemAsync(TOKEN_KEY),

  getUser: async () => {
    const raw = await SecureStore.getItemAsync(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },

  setUser: (user: object) =>
    SecureStore.setItemAsync(USER_KEY, JSON.stringify(user)),

  clearAll: async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(USER_KEY);
  },
};
