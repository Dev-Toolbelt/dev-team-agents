---
name: react-native-navigation
description: React Navigation rules for React Native — type safety, deep links, back behavior, and screen transitions.
---

## React Navigation

**Detection**: `@react-navigation/native` in `package.json`.

```tsx
// Root navigator pattern
<NavigationContainer>
  <RootStack.Navigator>
    <RootStack.Screen name="Auth" component={AuthStack} />
    <RootStack.Screen name="App" component={AppTabs} />
  </RootStack.Navigator>
</NavigationContainer>
```

## Rules

- **Type all navigation props**: use `NativeStackScreenProps<RootStackParamList, 'ScreenName'>` — never use `any` for navigation or route params
- **Deep links**: configure `linking` prop on `NavigationContainer`; test with `npx uri-scheme open` during development
- **Back behavior**: always handle Android hardware back button via `useBackHandler` or `BackHandler` when a custom behavior is needed
- **Screen transitions**: prefer the default platform transitions; custom animations must be tested on low-end devices for jank
