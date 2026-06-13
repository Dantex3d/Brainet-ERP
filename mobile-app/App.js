import React from 'react';
import { StyleSheet, View, ActivityIndicator, Text, Platform, Linking } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { WebView } from 'react-native-webview';

const APP_URL = process.env.APP_URL || 'https://your-deployed-brainet-site.com';

export default function App() {
  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <WebView
        source={{ uri: APP_URL }}
        startInLoadingState={true}
        renderLoading={() => (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color="#0d6efd" />
            <Text style={styles.loadingText}>Loading Brainet ERP...</Text>
          </View>
        )}
        renderError={() => (
          <View style={styles.errorContainer}>
            <Text style={styles.errorTitle}>Unable to load Brainet</Text>
            <Text style={styles.errorText}>
              Make sure the web system is running at:
            </Text>
            <Text style={styles.errorUrl}>{APP_URL}</Text>
            <Text style={styles.errorText}>
              Or set the APP_URL environment variable to your deployed site.
            </Text>
            <Text style={styles.openLink} onPress={() => Linking.openURL('https://expo.dev')}>Learn more</Text>
          </View>
        )}
        originWhitelist={['*']}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b1220',
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 16,
    color: '#ffffff',
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#0b1220',
  },
  errorTitle: {
    color: '#ff6b6b',
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 16,
  },
  errorText: {
    color: '#d1d5db',
    fontSize: 16,
    marginBottom: 12,
  },
  errorUrl: {
    color: '#66b2ff',
    fontSize: 15,
    marginBottom: 20,
  },
  openLink: {
    color: '#3b82f6',
    fontSize: 16,
    textDecorationLine: 'underline',
  },
});
