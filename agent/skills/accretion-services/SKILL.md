---
name: accretion-services
description: "Built-in sign-in and Supabase for the app, with no key from the user. Use when the app lets people sign in (Google or email link), or when the project has a Supabase database connected (project_secrets lists SUPABASE_URL)."
---

# Accretion services

Every app gets these from the platform. The values are in the app's environment (only its running
services have them; your commands do not). Never ask the user for an email or Google key for
sign-in, never print the values, and never put them in code.

| Need | Use | Environment |
|---|---|---|
| Sign-in | Redirect to the sign-in page, verify the returned token | `ACCRETION_APP_ID`, `ACCRETION_API_URL` and their `VITE_` / `NEXT_PUBLIC_` copies |
| Database | Supabase, once the user connects it | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, public `…SUPABASE_URL`, `…SUPABASE_PUBLISHABLE_KEY` |

Call every service from server code. The only values a page may read are the public `VITE_` /
`NEXT_PUBLIC_` ones.

## Sign-in

Offer both buttons. Google sign-in is refused inside in-app browsers (Instagram, LinkedIn, Gmail), so
the email link must always be there.

1. Google: send the browser to
   `{ACCRETION_API_URL}/apps/{ACCRETION_APP_ID}/auth/google?redirect_uri=<this app's callback URL>`.
2. Email link: the page posts the address to your own server, which calls
   `POST {ACCRETION_API_URL}/apps/{ACCRETION_APP_ID}/auth/email`
   `{"email": "…", "redirect_uri": "<callback URL>"}` with `Authorization: Bearer {ACCRETION_APP_TOKEN}`.
   Then show "Check your email". Pages cannot call
   the platform directly: its API refuses other sites' pages.
3. Both return to the callback URL with `#accretion_token=<token>` in the address. Read it in the
   page, send it once to your own server, and remove it from the address.
4. On the server, verify the token: a JWT signed with EdDSA, keys at
   `{ACCRETION_API_URL}/apps/auth/jwks.json`, issuer `{ACCRETION_API_URL}/apps`, audience
   `ACCRETION_APP_ID` (use `jose` in Node, `PyJWT[crypto]` in Python). Or, from the server, call
   `GET {ACCRETION_API_URL}/apps/{ACCRETION_APP_ID}/auth/session` with
   `Authorization: Bearer <token>` and read the user from the reply.
5. The claims give `sub` (a stable id for this person in this app), `email`, `name`, `picture`. Store
   your own user row keyed by `sub`, then use the app's usual session cookie signed with `APP_SECRET`.

Never add a route, button or flag that signs someone in without a platform token, not even for a test.
To check your work, open the signed-out page and check that each sign-in button goes to the start URL;
ask the user to try the sign-in. Read `APP_SECRET` from the environment and fail when it is missing;
never fall back to a fixed value.

The callback URL must be on the app's own address. Use the page's own origin, never a fixed host.

## Supabase

When project_secrets lists `SUPABASE_URL`, the user connected Supabase and `DATABASE_URL` points at it.
Keep using the project's migration setup: the host applies new migrations to Supabase, asks the user
before any change that deletes data, and returns Supabase's security findings. Fix each finding in a
new migration, for example turn on row level security for a table the page reads with the publishable key:

```sql
alter table public.notes enable row level security;
create policy "Owners read their notes" on public.notes for select using (auth.uid() = user_id);
```

Use `query_database` to read tables, columns, policies and rows. It cannot change anything.
In the page, `@supabase/supabase-js` takes the public URL and publishable key; never use
`SUPABASE_SECRET_KEY` in the page. Supabase Auth emails go out through the platform's email service.
