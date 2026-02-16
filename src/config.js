export function getConfig() {
  return {
    primary: {
      host: process.env.PRIMARY_HOST ?? 'localhost',
      port: Number(process.env.PRIMARY_PORT ?? 5432),
      user: process.env.POSTGRES_USER ?? 'app',
      password: process.env.POSTGRES_PASSWORD ?? 'app_password',
      database: process.env.POSTGRES_DB ?? 'appdb'
    },
    replica: {
      host: process.env.REPLICA_HOST ?? 'localhost',
      port: Number(process.env.REPLICA_PORT ?? 5433),
      user: process.env.POSTGRES_USER ?? 'app',
      password: process.env.POSTGRES_PASSWORD ?? 'app_password',
      database: process.env.POSTGRES_DB ?? 'appdb'
    }
  };
}
