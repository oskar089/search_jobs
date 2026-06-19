import { api } from "./api";
import type { Profile, ProfileUpdate } from "../types";

export async function getMyProfile(): Promise<Profile> {
  return api<Profile>("/profiles");
}

export async function updateMyProfile(data: ProfileUpdate): Promise<Profile> {
  return api<Profile>("/profiles", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
