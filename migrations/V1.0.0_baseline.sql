--
-- PostgreSQL database dump
--

-- Dumped from database version 15.3 (Debian 15.3-1.pgdg120+1)
-- Dumped by pg_dump version 15.3 (Debian 15.3-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: player_mention_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.player_mention_type AS ENUM (
    'MENTION',
    'IGN',
    'DISCORD_NAME'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event (
    id integer NOT NULL,
    event_start bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    description text NOT NULL,
    title text NOT NULL,
    max_players smallint NOT NULL,
    weekly boolean DEFAULT false NOT NULL,
    last_dispatch bigint,
    guild_event_id bigint,
    creator_id bigint NOT NULL,
    server_id bigint NOT NULL,
    advanced_settings json,
    state smallint DEFAULT 0 NOT NULL
);


--
-- Name: event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_id_seq OWNED BY public.event.id;


--
-- Name: eventpreset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eventpreset (
    id integer NOT NULL,
    name text NOT NULL,
    title text,
    description text,
    max_players smallint,
    server_id bigint NOT NULL,
    advanced_settings json,
    partial boolean DEFAULT false
);


--
-- Name: eventpreset_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eventpreset_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eventpreset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eventpreset_id_seq OWNED BY public.eventpreset.id;


--
-- Name: eventregister; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eventregister (
    id integer NOT NULL,
    substitute boolean DEFAULT false NOT NULL,
    registered_at bigint NOT NULL,
    character_id integer NOT NULL,
    event_id integer NOT NULL,
    user_id bigint NOT NULL,
    notified boolean DEFAULT false NOT NULL,
    notify_before integer DEFAULT 300 NOT NULL
);


--
-- Name: eventregister_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eventregister_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eventregister_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eventregister_id_seq OWNED BY public.eventregister.id;

--
-- Name: messagedeletequeue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messagedeletequeue (
    id bigint NOT NULL,
    delete_at bigint,
    channel_id bigint
);


--
-- Name: messagedeletequeue_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.messagedeletequeue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: messagedeletequeue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.messagedeletequeue_id_seq OWNED BY public.messagedeletequeue.id;


--
-- Name: playercharacter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.playercharacter (
    id integer NOT NULL,
    class_type smallint NOT NULL,
    character_name text NOT NULL,
    item_lvl bigint NOT NULL,
    user_id bigint NOT NULL,
    api_id integer,
    custom_guild text
);


--
-- Name: playercharacter_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.playercharacter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: playercharacter_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.playercharacter_id_seq OWNED BY public.playercharacter.id;


--
-- Name: server; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.server (
    id bigint NOT NULL,
    lang text NOT NULL,
    role_assign boolean DEFAULT false NOT NULL,
    event_creator_role_id bigint,
    manager_role bigint,
    time_offset integer DEFAULT 0,
    delete_delay smallint DEFAULT '-1'::integer,
    log_channel bigint,
    event_player_mention public.player_mention_type DEFAULT 'IGN'::public.player_mention_type NOT NULL
);


--
-- Name: server_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.server_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.server_id_seq OWNED BY public.server.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    main_class integer,
    notify_before integer DEFAULT 300 NOT NULL,
    twitch_id text
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

ALTER TABLE ONLY public.event ALTER COLUMN id SET DEFAULT nextval('public.event_id_seq'::regclass);


--
-- Name: eventpreset id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventpreset ALTER COLUMN id SET DEFAULT nextval('public.eventpreset_id_seq'::regclass);


--
-- Name: eventregister id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventregister ALTER COLUMN id SET DEFAULT nextval('public.eventregister_id_seq'::regclass);



--
-- Name: messagedeletequeue id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messagedeletequeue ALTER COLUMN id SET DEFAULT nextval('public.messagedeletequeue_id_seq'::regclass);


--
-- Name: playercharacter id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playercharacter ALTER COLUMN id SET DEFAULT nextval('public.playercharacter_id_seq'::regclass);


--
-- Name: server id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.server ALTER COLUMN id SET DEFAULT nextval('public.server_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: event event_guild_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_guild_event_id_key UNIQUE (guild_event_id);


--
-- Name: event event_message_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_message_id_key UNIQUE (message_id);


--
-- Name: event event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_pkey PRIMARY KEY (id);


--
-- Name: eventpreset eventpreset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventpreset
    ADD CONSTRAINT eventpreset_pkey PRIMARY KEY (id);


--
-- Name: eventregister eventregister_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventregister
    ADD CONSTRAINT eventregister_pkey PRIMARY KEY (id);

--
-- Name: playercharacter playercharacter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playercharacter
    ADD CONSTRAINT playercharacter_pkey PRIMARY KEY (id);


--
-- Name: server server_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.server
    ADD CONSTRAINT server_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

--
-- Name: event event_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: event event_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.server(id) ON DELETE CASCADE;


--
-- Name: eventpreset eventpreset_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventpreset
    ADD CONSTRAINT eventpreset_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.server(id) ON DELETE CASCADE;


--
-- Name: eventregister eventregister_character_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventregister
    ADD CONSTRAINT eventregister_character_id_fkey FOREIGN KEY (character_id) REFERENCES public.playercharacter(id) ON DELETE CASCADE;


--
-- Name: eventregister eventregister_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventregister
    ADD CONSTRAINT eventregister_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.event(id) ON DELETE CASCADE;


--
-- Name: eventregister eventregister_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eventregister
    ADD CONSTRAINT eventregister_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

--
-- Name: playercharacter playercharacter_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playercharacter
    ADD CONSTRAINT playercharacter_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

