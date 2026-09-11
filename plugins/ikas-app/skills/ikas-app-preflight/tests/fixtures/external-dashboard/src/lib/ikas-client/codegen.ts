import type { CodegenConfig } from '@graphql-codegen/cli';
import { preset } from '@ikas/admin-api-client';

const config: CodegenConfig = {
  schema: {
    'https://api.myikas.com/api/v2/admin/graphql': {
      headers: {
        'Content-Type': 'application/json',
      },
    },
  },
  documents: ['src/lib/ikas-client/**/*.ts'],
  generates: {
    'src/lib/ikas-client/generated/graphql.ts': {
      preset,
      plugins: [],
      presetConfig: {
        gqlTagName: 'gql',
      },
    },
  },
};

export default config;
